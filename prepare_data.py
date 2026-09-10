"""Reproducible, grain-safe preparation of the eleven supplied CSV files."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent


# Great-circle distance between two lat/lon points in km 
def haversine(lat1, lon1, lat2, lon2):
    a, b, c, d = map(np.radians, [lat1, lon1, lat2, lon2])
    h = np.sin((c-a)/2)**2 + np.cos(a)*np.cos(c)*np.sin((d-b)/2)**2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))

def prepare(raw=ROOT/'data/raw', out=ROOT/'data/processed'):
    raw, out = Path(raw), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    audit = {'sources': {}, 'checks': {}, 'issues': {}}
    def read(name):
        path = raw / (name+'.csv')
        d = pd.read_csv(path, encoding='utf-8-sig', dtype={
            'customer_zip_code_prefix':str, 'seller_zip_code_prefix':str,
            'geolocation_zip_code_prefix':str})
        audit['sources'][name] = {'rows':len(d), 'columns':list(d.columns),
            'exact_duplicates':int(d.duplicated().sum()),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        return d
    o = read('orders_dataset')
    c = read('customers_dataset')
    s = read('sellers_dataset')
    p = read('products_dataset')
    tr = read('product_category_name_translation')
    i = read('order_items_dataset')
    pay = read('order_payments_dataset')
    rev = read('order_reviews_dataset')
    geo = read('geolocation_dataset')
    leads = read('marketing_qualified_leads_dataset')
    deals = read('closed_deals_dataset')
    for frame, key in [(o,'order_id'),(c,'customer_id'),(s,'seller_id'),(p,'product_id'),
                       (leads,'mql_id'),(deals,'mql_id'),(deals,'seller_id')]:
        assert frame[key].notna().all() and frame[key].is_unique, key
    assert not i.duplicated(['order_id','order_item_id']).any()
    audit['issues']['extra_review_rows_per_order'] = int(rev.order_id.duplicated().sum())
    audit['issues']['non_unique_review_ids'] = int(rev.review_id.duplicated().sum())
    for frame, key, parent in [(i,'order_id',o),(i,'seller_id',s),(i,'product_id',p),
                                (o,'customer_id',c),(pay,'order_id',o),(rev,'order_id',o),
                                (deals,'mql_id',leads)]:
        assert frame[key].isin(parent[key]).all(), f'Orphan {key}'
    for col in [x for x in o if x.endswith('_date') or x.endswith('_timestamp') or x=='order_approved_at']:
        o[col] = pd.to_datetime(o[col], errors='coerce')
    for col in ['review_creation_date','review_answer_timestamp']:
        rev[col] = pd.to_datetime(rev[col], errors='coerce')
    # Latest answered review per order, with deterministic tie breaking.
    rev = rev.sort_values(['review_answer_timestamp','review_creation_date','review_id'],
                          na_position='first').drop_duplicates('order_id',keep='last')
    text = rev.review_comment_title.fillna('').str.strip()+' '+rev.review_comment_message.fillna('').str.strip()
    rev['has_written_comment'] = text.str.strip().ne('')
    rev['comment_length'] = text.str.strip().str.len()
    # Do not present an unvalidated Portuguese NLP model as text sentiment.
    rev['rating_sentiment'] = np.select([rev.review_score.le(2),rev.review_score.eq(3)],
                                        ['Negative (1–2)','Neutral (3)'], default='Positive (4–5)')
    payments = pay.groupby('order_id').agg(payment_value=('payment_value','sum'),
        payment_installments=('payment_installments','max'), payment_records=('order_id','size'))
    types = pay.groupby('order_id').payment_type.agg(lambda x:'|'.join(sorted(set(x.dropna()))))
    primary = pay.sort_values(['payment_value','payment_type'],ascending=[False,True]).drop_duplicates('order_id')
    payments = payments.join(types.rename('payment_types')).join(primary.set_index('order_id').payment_type)
    o = o.merge(c,on='customer_id',validate='one_to_one').merge(payments,on='order_id',how='left',validate='one_to_one')
    o = o.merge(rev[['order_id','review_score','has_written_comment','comment_length','rating_sentiment']],
                on='order_id',how='left',validate='one_to_one')
    def days(end, start): return (o[end]-o[start]).dt.total_seconds()/86400
    o['approval_time'] = days('order_approved_at','order_purchase_timestamp')
    o['processing_time'] = days('order_delivered_carrier_date','order_approved_at')
    o['carrier_time'] = days('order_delivered_customer_date','order_delivered_carrier_date')
    o['delivery_time'] = days('order_delivered_customer_date','order_purchase_timestamp')
    for col in ['approval_time','processing_time','carrier_time','delivery_time']:
        audit['issues']['negative_'+col] = int(o[col].lt(0).sum())
        o.loc[o[col].lt(0),col] = np.nan
    o['delivery_estimate_mismatch'] = days('order_delivered_customer_date','order_estimated_delivery_date')
    # Promise timestamps are midnight dates. Use calendar days for promise adherence.
    o['delay_days'] = (o.order_delivered_customer_date.dt.normalize()-o.order_estimated_delivery_date.dt.normalize()).dt.days
    eligible = o.order_status.eq('delivered') & o.delivery_time.notna() & o.delay_days.notna()
    o['late_flag'] = np.where(eligible,o.delay_days.gt(0).astype(float),np.nan)
    o['delivery_status'] = np.select([eligible & o.delay_days.lt(0),eligible & o.delay_days.eq(0),eligible & o.delay_days.gt(0)],
                                     ['Early','On time','Late'], default='Unobserved')
    o['one_star'] = np.where(o.review_score.notna(),o.review_score.eq(1).astype(float),np.nan)
    o['low_rating'] = np.where(o.review_score.notna(),o.review_score.le(2).astype(float),np.nan)
    o['month'] = o.order_purchase_timestamp.dt.to_period('M').astype(str)
    o['installment_flag'] = np.where(o.payment_installments.notna(),o.payment_installments.gt(1).astype(float),np.nan)
    for frame,col in [(geo,'geolocation_zip_code_prefix'),(c,'customer_zip_code_prefix'),
                      (s,'seller_zip_code_prefix'),(o,'customer_zip_code_prefix')]:
        frame[col] = frame[col].astype('string').str.zfill(5)
    # Clean up geolocation table and get median coordinates per zip code
    geo = geo.drop_duplicates()
    valid_geo = geo.geolocation_lat.between(-34,6) & geo.geolocation_lng.between(-74,-32)
    audit['issues']['coordinates_outside_brazil_bounds'] = int((~valid_geo).sum())
    g = geo[valid_geo].groupby('geolocation_zip_code_prefix')[['geolocation_lat','geolocation_lng']].median()
    o = o.merge(g.rename(columns={'geolocation_lat':'customer_lat','geolocation_lng':'customer_lon'}),
        left_on='customer_zip_code_prefix',right_index=True,how='left',validate='many_to_one')
    s = s.merge(g.rename(columns={'geolocation_lat':'seller_lat','geolocation_lng':'seller_lon'}),
        left_on='seller_zip_code_prefix',right_index=True,how='left',validate='many_to_one')
    p = p.merge(tr,on='product_category_name',how='left',validate='many_to_one')
    p['category'] = p.product_category_name_english.fillna(p.product_category_name).fillna('unknown').str.replace('_',' ').str.title()
    p['product_volume_cm3'] = p.product_length_cm*p.product_width_cm*p.product_height_cm
    i = i.merge(p,on='product_id',how='left',validate='many_to_one').merge(s,on='seller_id',how='left',validate='many_to_one')
    i['item_value'] = i.price+i.freight_value
    i['freight_ratio'] = i.freight_value.div(i.price.where(i.price.gt(0)))
    totals = i.groupby('order_id').agg(order_value=('item_value','sum'),merchandise_value=('price','sum'),
        order_freight=('freight_value','sum'),item_count=('order_id','size'),seller_count=('seller_id','nunique'),
        category_count=('category','nunique'))
    o = o.merge(totals,on='order_id',how='left',validate='one_to_one')
    # Delivered-customer history is fixed across filters; repeat orders differ from repeat buyers.
    hist = o[o.order_status.eq('delivered')].sort_values(['order_purchase_timestamp','order_id']).copy()
    hist['lifetime_order_seq'] = hist.groupby('customer_unique_id').cumcount()+1
    cust = hist.groupby('customer_unique_id').agg(customer_order_count=('order_id','size'),
        lifetime_order_value=('order_value','sum'),first_purchase=('order_purchase_timestamp','min'))
    cust['repeat_buyer'] = cust.customer_order_count.gt(1)
    second = hist[hist.lifetime_order_seq.eq(2)].set_index('customer_unique_id').order_purchase_timestamp
    cust['second_purchase'] = second
    cust['repeat_within_90d'] = (cust.second_purchase-cust.first_purchase).dt.total_seconds().div(86400).le(90)
    cutoff = hist.order_purchase_timestamp.max()
    cust['mature_90d'] = cust.first_purchase.add(pd.Timedelta(days=90)).le(cutoff)
    o = o.merge(cust,on='customer_unique_id',how='left',validate='many_to_one')
    o = o.merge(hist[['order_id','lifetime_order_seq']],on='order_id',how='left',validate='one_to_one')
    o['is_repeat'] = o.lifetime_order_seq.gt(1)
    o['buyer_type'] = np.where(o.repeat_buyer.astype('boolean').fillna(False),'Repeat buyer','One-time buyer')
    o['value_band'] = pd.cut(o.order_value,[0,50,150,300,600,np.inf],
         labels=['Under R$50','R$50–150','R$150–300','R$300–600','R$600+'],include_lowest=True).astype('string')
    i = i.merge(o[['order_id','customer_lat','customer_lon']],on='order_id',validate='many_to_one')
    i['distance'] = haversine(i.seller_lat,i.seller_lon,i.customer_lat,i.customer_lon)
    i['freight_per_distance'] = i.freight_value.div(i.distance.where(i.distance.ge(1)))
    route = i.groupby(['order_id','seller_id']).distance.first().groupby('order_id').mean()
    o = o.merge(route.rename('distance'),on='order_id',how='left',validate='one_to_one')
    o['freight_per_distance'] = o.order_freight.div(o.distance.where(o.distance.ge(1)))
    o['freight_burden'] = o.order_freight.div(o.merchandise_value.where(o.merchandise_value.gt(0)))
    i['shipping_limit_date'] = pd.to_datetime(i.shipping_limit_date,errors='coerce')
    i = i.drop(columns=['customer_lat','customer_lon'])
    leads['first_contact_date'] = pd.to_datetime(leads.first_contact_date)
    deals['won_date'] = pd.to_datetime(deals.won_date)
    leads['origin'] = leads.origin.fillna('unknown').str.replace('_',' ').str.title()
    # Combine leads with closed deals to track seller acquisition
    m = leads.merge(deals,on='mql_id',how='left',validate='one_to_one')
    m['converted'] = m.seller_id.notna()
    m['conversion_days'] = (m.won_date-m.first_contact_date).dt.total_seconds()/86400
    m['matched_seller'] = m.seller_id.isin(i.seller_id)
    m['conversion_cohort'] = pd.cut(m.conversion_days,[-1,7,30,90,np.inf],
        labels=['0–7 days','8–30 days','31–90 days','91+ days']).astype('string')
    m['mature_90d'] = (m.won_date+pd.Timedelta(days=90)).le(cutoff)
    sales = i.merge(o[['order_id','order_purchase_timestamp','order_status','review_score','late_flag']],on='order_id',validate='many_to_one')
    sales = sales.merge(m[['seller_id','won_date']].dropna(subset=['seller_id']),on='seller_id',how='inner',validate='many_to_one')
    sales['days_after_won'] = (sales.order_purchase_timestamp-sales.won_date).dt.total_seconds()/86400
    post = sales[sales.days_after_won.between(0,90,inclusive='left') & sales.order_status.eq('delivered')]
    seller_orders = post.drop_duplicates(['seller_id','order_id'])
    a = post.groupby('seller_id').agg(value_90d=('item_value','sum'))
    a = a.join(seller_orders.groupby('seller_id').agg(orders_90d=('order_id','size'),rating_90d=('review_score','mean'),
        reviews_90d=('review_score','count'),late_90d=('late_flag','mean'),deliveries_90d=('late_flag','count')))
    m = m.merge(a,on='seller_id',how='left',validate='many_to_one')
    for col in ['value_90d','orders_90d','reviews_90d','deliveries_90d']: m[col] = m[col].fillna(0)
    # Final data integrity checks before saving
    audit['checks'] = {'order_grain_unique':bool(o.order_id.is_unique),
        'item_grain_unique':bool(not i.duplicated(['order_id','order_item_id']).any()),
        'item_count_preserved':len(i)==audit['sources']['order_items_dataset']['rows'],
        'order_count_preserved':len(o)==audit['sources']['orders_dataset']['rows'],
        'order_item_value_reconciles':bool(np.isclose(o.order_value.sum(),i.item_value.sum())),
        'payment_total_reconciles':bool(np.isclose(o.payment_value.sum(),pay.payment_value.sum()))}
    audit['issues'].update({'orders_without_items':int(o.order_value.isna().sum()),
        'orders_without_review':int(o.review_score.isna().sum()),
        'items_without_distance':int(i.distance.isna().sum()),
        'orders_with_multiple_sellers':int(o.seller_count.gt(1).sum()),
        'orders_with_multiple_categories':int(o.category_count.gt(1).sum()),
        'payment_value_differs_from_item_total_gt_1brl':int((o.payment_value-o.order_value).abs().gt(1).sum()),
        'closed_sellers':int(m.converted.sum()),'matched_closed_sellers':int(m.matched_seller.sum()),
        'closed_sellers_with_pre_won_sales':int(sales.loc[sales.days_after_won.lt(0),'seller_id'].nunique()),
        'declared_revenue_zero':int(deals.declared_monthly_revenue.eq(0).sum()),
        'declared_catalog_missing':int(deals.declared_product_catalog_size.isna().sum())})
    audit['coverage'] = {'purchase_start':str(o.order_purchase_timestamp.min()),
        'purchase_end':str(o.order_purchase_timestamp.max()),'last_delivered_purchase':str(cutoff),
        'lead_start':str(leads.first_contact_date.min()),'lead_end':str(leads.first_contact_date.max()),
        'won_end':str(deals.won_date.max()),'status_counts':o.order_status.value_counts().to_dict()}
    o.to_parquet(out/'orders.parquet',index=False)
    i.to_parquet(out/'items.parquet',index=False)
    m.to_parquet(out/'marketing.parquet',index=False)
    sales.to_parquet(out/'acquired_sales.parquet',index=False)
    (out/'quality.json').write_text(json.dumps(audit,indent=2,default=str),encoding='utf-8')
    assert all(audit['checks'].values()), audit['checks']
    print(json.dumps({'checks':audit['checks'],'issues':audit['issues'],'coverage':audit['coverage']},indent=2))
    return o,i,m


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--raw',type=Path,default=ROOT/'data/raw')
    parser.add_argument('--out',type=Path,default=ROOT/'data/processed')
    args=parser.parse_args()
    prepare(args.raw,args.out)
