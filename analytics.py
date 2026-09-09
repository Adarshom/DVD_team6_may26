"""Shared metric definitions and chart builders. All value measures are BRL."""
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT=Path(__file__).resolve().parent
TEAL='#117B75'; RED='#C85646'; GOLD='#BC861F'; INK='#223A39'; BLUE='#6185AA'
PALETTE=[TEAL,RED,GOLD,BLUE,'#9387AE','#7F9B7C']
COLORS={'Early':TEAL,'On time':BLUE,'Late':RED,'Unobserved':'#9DA7A3',
        'Fix':RED,'Protect':TEAL,'Explore growth':BLUE,'Investigate':GOLD,
        'One-time buyer':BLUE,'Repeat buyer':TEAL,'1':RED,'2':'#D99C65','3':GOLD,'4':'#77A49B','5':TEAL}
px.defaults.color_discrete_sequence=PALETTE
LABELS={'value':'Gross order value (R$)','rating':'Average review / 5','low_rate':'Low-rating share (%)',
 'value_band':'Full order value band','demand_pressure':'Orders / (local sellers + 1)',
 'late_rate':'Late deliveries (%)','orders':'Orders','reviews':'Reviewed orders','distance':'Straight-line distance (km)',
 'delivery_time':'Purchase to delivery (days)','delay_days':'Days after promised date','category':'Product category',
 'customer_state':'Customer state','seller_state':'Seller state','seller_id':'Seller ID','freight_burden':'Freight / merchandise (%)',
 'freight_ratio':'Freight / merchandise (%)','freight_value':'Item freight (R$)','order_value':'Full order value (R$)',
 'item_value':'Item value incl. freight (R$)','processing_time':'Seller handling (days)','month':'Purchase month',
 'origin':'Lead source','conversion_days':'Contact to win (days)','value_90d':'Observed 90-day value (R$)',
 'orders_90d':'Observed 90-day orders','rating_90d':'90-day average review','conversion_cohort':'Contact-to-win cohort',
 'product_weight_g':'Product weight (g)','product_volume_cm3':'Product volume (cm³)',
 'product_photos_qty':'Photo count','product_description_lenght':'Description length',
 'payment_installments':'Maximum installments / order','has_written_comment':'Written review',
 'one_star':'One-star orders','low_count':'Low-rated orders','late_count':'Late orders'}


def load():
    if not (ROOT/'data/processed/orders.parquet').exists():
        from prepare_data import prepare
        prepare()
    return tuple(pd.read_parquet(ROOT/'data/processed'/f'{x}.parquet') for x in ['orders','items','marketing'])


def filter_data(orders,items,start=None,end=None,categories=None,states=None,seller_states=None,
                sellers=None,statuses=None,payments=None,delivery=None,values=None,threshold=2):
    o=orders.copy()
    if start: o=o[o.order_purchase_timestamp.ge(pd.Timestamp(start))]
    if end: o=o[o.order_purchase_timestamp.lt(pd.Timestamp(end)+pd.Timedelta(days=1))]
    for col,vals in [('customer_state',states),('order_status',statuses),('delivery_status',delivery),('value_band',values)]:
        if vals: o=o[o[col].isin(vals)]
    if payments:
        o=o[o.payment_types.fillna('').map(lambda s: bool(set(s.split('|')) & set(payments)))]
    f=items[items.order_id.isin(o.order_id)].copy()
    for col,vals in [('category',categories),('seller_state',seller_states),('seller_id',sellers)]:
        if vals: f=f[f[col].isin(vals)]
    # Only item-scoped selections remove itemless orders from the order cohort.
    if categories or seller_states or sellers: o=o[o.order_id.isin(f.order_id)].copy()
    o['low_rating']=np.where(o.review_score.notna(),o.review_score.le(threshold).astype(float),np.nan)
    cols=[c for c in o if c not in f or c=='order_id']
    f=f.merge(o[cols],on='order_id',how='inner',validate='many_to_one')
    return o,f


def metrics(f,keys):
    keys=[keys] if isinstance(keys,str) else keys
    d=f.drop_duplicates(keys+['order_id'])
    a=d.groupby(keys,dropna=False,observed=True).agg(orders=('order_id','size'),reviews=('review_score','count'),
       rating=('review_score','mean'),low_rate=('low_rating','mean'),low_count=('low_rating','sum'),
       late_rate=('late_flag','mean'),late_count=('late_flag','sum'),deliveries=('late_flag','count'),
       one_star=('one_star','sum'),delivery_time=('delivery_time','mean'),distance=('distance','mean'))
    a=a.join(f.groupby(keys,dropna=False,observed=True).agg(value=('item_value','sum'),freight=('freight_value','sum'),
            merchandise=('price','sum'),sellers=('seller_id','nunique'))).reset_index()
    a['low_rate']*=100; a['late_rate']*=100
    a['freight_burden']=100*a.freight.div(a.merchandise.where(a.merchandise.gt(0)))
    a['review_coverage']=100*a.reviews/a.orders
    # Mean selected route per order, then mean across orders within a segment.
    route_keys=list(dict.fromkeys(keys+['order_id','seller_id']))
    routes=f.drop_duplicates(route_keys).groupby(keys+['order_id'],dropna=False,observed=True).distance.mean()
    distances=routes.groupby(level=list(range(len(keys)))).mean().rename('distance').reset_index()
    a=a.drop(columns='distance').merge(distances,on=keys,how='left')
    return a


def money(v):
    if pd.isna(v): return 'N/A'
    return f'R${v/1e6:,.2f}m' if abs(v)>=1e6 else (f'R${v/1000:,.1f}k' if abs(v)>=1000 else f'R${v:,.0f}')


def pct(v): return 'N/A' if pd.isna(v) else f'{v:.1f}%'
def number(v): return 'N/A' if pd.isna(v) else f'{v:,.0f}'


def style(fig):
    fig.update_layout(template='plotly_white',paper_bgcolor='white',plot_bgcolor='white',
      font=dict(family='Arial, sans-serif',size=12,color=INK),margin=dict(l=24,r=24,t=36,b=55),
      legend=dict(orientation='h',y=1.12,x=0,title_text=''),height=365,
      coloraxis_colorbar=dict(thickness=10,len=.75),hoverlabel=dict(bgcolor='white'),
      modebar_remove=['lasso2d','select2d'])
    fig.update_xaxes(gridcolor='#EEF1EE',zeroline=False,automargin=True)
    fig.update_yaxes(gridcolor='#EEF1EE',zeroline=False,automargin=True)
    return fig


def empty(msg='No eligible observations. Broaden the filters or lower the minimum sample.'):
    fig=go.Figure(); fig.add_annotation(text=msg,x=.5,y=.5,xref='paper',yref='paper',showarrow=False,font=dict(size=14,color='#647A77'))
    fig.update_xaxes(visible=False);fig.update_yaxes(visible=False)
    return style(fig)


def scatter(d,x,y,size=None,color=None,hover=None,quadrant=False):
    d=d.dropna(subset=[x,y]).copy()
    if d.empty:return empty()
    if size:d[size]=d[size].fillna(0).clip(lower=0)
    scale=['#F3E7D9',RED] if color in ['late_rate','low_rate','late_change_pp'] else ['#BCE0D2',TEAL]
    fig=px.scatter(d,x=x,y=y,size=size,color=color,hover_name=hover,size_max=42,opacity=.78,
        labels=LABELS,color_discrete_map=COLORS,color_continuous_scale=scale,hover_data={x:':,.2f',y:':,.2f'})
    if quadrant:
        fig.add_vline(x=d[x].median(),line_dash='dot',line_color='#B7C7C0')
        fig.add_hline(y=d[y].median(),line_dash='dot',line_color='#B7C7C0')
    return style(fig)


def bar(d,x,y,color=None,top=15,horizontal=True):
    if d.empty:return empty()
    d=d.nlargest(top,y).sort_values(y)
    if x=='seller_id':
        d=d.copy();d['seller_label']=d.seller_id.str[:8]; hover='seller_id'; xx='seller_label'
    else: hover=x;xx=x
    fig=px.bar(d,x=y if horizontal else xx,y=xx if horizontal else y,
        orientation='h' if horizontal else 'v',color=color,hover_name=hover,labels=LABELS,
        color_discrete_sequence=[TEAL],color_continuous_scale=['#BCE0D2',TEAL])
    if x=='seller_id':fig.update_yaxes(title_text='Seller (ID prefix)')
    return style(fig)


def heat(d,row,col,val,minimum=0,count='orders',center=None):
    if minimum and count in d:d=d[d[count].ge(minimum)]
    if d.empty:return empty()
    p=d.pivot_table(index=row,columns=col,values=val,aggfunc='mean',observed=True)
    if col=='delay_bucket':
        def lower(v):return float(str(v).lstrip('([').split(',')[0])
        p=p.reindex(columns=sorted(p.columns,key=lower))
    if col=='value_band':p=p.reindex(columns=[x for x in ['Under R$50','R$50–150','R$150–300','R$300–600','R$600+'] if x in p.columns])
    if len(p)>18:
        ranks=d.groupby(row)[count].sum().nlargest(18).index if count in d else p.index[:18]
        p=p.reindex(ranks)
    scale=('RdYlGn' if val in ['rating','rating_90d'] else 'RdYlGn_r') if center is None else 'RdBu'
    fig=px.imshow(p,color_continuous_scale=scale,color_continuous_midpoint=center,
        aspect='auto',labels={'color':LABELS.get(val,val),'x':LABELS.get(col,col),'y':LABELS.get(row,row)})
    fig.update_traces(hovertemplate='%{y} · %{x}<br>%{z:.2f}<extra></extra>')
    return style(fig)


def binned(o,x,y='review_score',bins=None,min_n=30):
    d=o[[x,y]].dropna().copy()
    if d.empty:return empty(),pd.DataFrame()
    if bins is None:
        try:d['bucket']=pd.qcut(d[x],8,duplicates='drop')
        except ValueError:return empty(),pd.DataFrame()
    else:d['bucket']=pd.cut(d[x],bins,include_lowest=True)
    a=d.groupby('bucket',observed=True).agg(mean=(y,'mean'),n=(y,'size'),std=(y,'std'),x=(x,'median')).reset_index()
    a=a[a.n.ge(min_n)].copy()
    if a.empty:return empty(),a
    a['ci']=1.96*a['std'].fillna(0)/np.sqrt(a.n);a['bucket']=a.bucket.astype(str)
    fig=px.line(a,x='x',y='mean',markers=True,error_y='ci',custom_data=['n','bucket'],
        labels={'x':LABELS.get(x,x),'mean':LABELS.get(y,'Average review / 5')})
    fig.update_traces(hovertemplate='%{customdata[1]}<br>Mean: %{y:.2f}<br>n=%{customdata[0]:,}<extra></extra>',line_color=TEAL)
    return style(fig),a


def pareto(d,key,val):
    d=d.sort_values(val,ascending=False).copy()
    if d.empty or d[val].sum()<=0:return empty()
    d['rank']=np.arange(1,len(d)+1);d['cumulative']=100*d[val].cumsum()/d[val].sum()
    fig=go.Figure(go.Scatter(x=d['rank'],y=d.cumulative,mode='lines',fill='tozeroy',line_color=TEAL,
          customdata=d[[key,val]],hovertemplate='Rank %{x}<br>%{customdata[0]}<br>Value %{customdata[1]:,.1f}<br>Cumulative %{y:.1f}%<extra></extra>'))
    fig.add_hline(y=80,line_dash='dot',line_color=GOLD)
    fig.update_layout(xaxis_title=f'{LABELS.get(key,key)} ranked by {LABELS.get(val,val).lower()}',yaxis_title='Cumulative share (%)')
    return style(fig)


def rating_mix(o,group):
    d=o.dropna(subset=['review_score',group]).copy()
    if d.empty:return empty()
    d['Stars']=d.review_score.astype(int).astype(str)
    a=d.groupby([group,'Stars'],observed=True).size().rename('n').reset_index()
    a['share']=100*a.n/a.groupby(group).n.transform('sum')
    fig=px.bar(a,x=group,y='share',color='Stars',custom_data=['n'],
      color_discrete_map=COLORS,category_orders={'Stars':['1','2','3','4','5'],'delivery_status':['Early','On time','Late']},
      labels={'share':'Share of reviewed orders (%)',group:group.replace('_',' ').title()})
    fig.update_traces(hovertemplate='%{x}<br>%{y:.1f}% · n=%{customdata[0]:,}<extra></extra>')
    return style(fig)


def box_summary(d,x,y,labels=None):
    """Render exact box summaries without sending hundreds of thousands of points."""
    d=d[[x,y]].dropna()
    if d.empty:return empty()
    rows=[]
    for group,part in d.groupby(x,observed=True,sort=False):
        vals=part[y];q1,med,q3=vals.quantile([.25,.5,.75]);iqr=q3-q1
        inside=vals[vals.between(q1-1.5*iqr,q3+1.5*iqr)]
        rows.append(dict(group=str(group),q1=q1,median=med,q3=q3,lower=inside.min(),upper=inside.max(),n=len(vals)))
    a=pd.DataFrame(rows)
    if x=='value_band':
        a['group']=pd.Categorical(a.group,['Under R$50','R$50–150','R$150–300','R$300–600','R$600+'],ordered=True);a=a.sort_values('group')
    elif x=='payment_installments':a=a.assign(sort_key=pd.to_numeric(a.group)).sort_values('sort_key')
    fig=go.Figure(go.Box(x=a.group,q1=a.q1,median=a['median'],q3=a.q3,lowerfence=a.lower,upperfence=a.upper,
        marker_color=TEAL,boxpoints=False,customdata=a.n,hovertemplate='%{x}<br>n=%{customdata:,}<extra></extra>'))
    labels=labels or LABELS
    fig.update_layout(xaxis_title=labels.get(x,x),yaxis_title=labels.get(y,y))
    return style(fig)


def result(insight,charts,table=None,note='',action=''):
    return {'insight':insight,'charts':charts,'table':pd.DataFrame() if table is None else table,'note':note,'action':action}


def overview(o,f,min_n=30):
    if o.empty:return result('No orders match this selection.',[('Broaden the filters',empty())])
    a=metrics(f,'category');a=a[a.reviews.ge(min_n)]
    monthly=metrics(f,'month')
    monthly.loc[monthly.reviews.lt(min_n),'low_rate']=np.nan
    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=.14)
    fig.add_trace(go.Bar(x=monthly.month,y=monthly.value,name='Gross order value',marker_color=TEAL),row=1,col=1)
    fig.add_trace(go.Scatter(x=monthly.month,y=monthly.low_rate,name='Low-rating share',line_color=RED,
       customdata=monthly.reviews,hovertemplate='%{x}<br>Low ratings %{y:.1f}%<br>Reviews %{customdata:,}<extra></extra>'),row=2,col=1)
    fig.update_yaxes(title_text='Value (R$)',row=1,col=1);fig.update_yaxes(title_text='Low ratings (%)',row=2,col=1)
    late=o[o.late_flag.eq(1)];on=o[o.late_flag.eq(0)]
    difference=100*(late.low_rating.mean()-on.low_rating.mean())
    insight=f'Late deliveries have a {pct(100*late.low_rating.mean())} low-rating share, versus {pct(100*on.low_rating.mean())} for deliveries meeting the promised date.'
    if late.review_score.count()<min_n or on.review_score.count()<min_n:insight='This selection has insufficient reviewed deliveries to compare late and on-time outcomes reliably.'
    return result(insight,[('Growth and customer experience',style(fig)),('Economic importance × dissatisfaction',scatter(a,'value','low_rate','orders','late_rate','category',True)),
        ('The delivery promise matters',rating_mix(o[o.delivery_status.ne('Unobserved')],'delivery_status')),('Where low-rated orders accumulate',bar(a,'category','low_count'))],
        a.sort_values('low_count',ascending=False),
        'These are past orders from the selected dates. Order value adds the price of the selected items and shipping; it is not the money the marketplace keeps. Low ratings follow your chosen star limit. Late orders may have worse reviews, but this alone does not show that lateness caused them. The first and last months have only partial records, so they cannot tell us how sales will grow.',
        'Investigate large categories and delivery lanes with both substantial value and repeated poor outcomes. Use the question pages to separate scale, service and acquisition risks.')


def final_question(n,o,f,m,min_n=30,scenario=50,top_n=10,**kwargs):
    if n not in [7,8,9] and o.empty:return result('No orders match this selection.',[('No data',empty())])
    if n==1:
        a=o.groupby('buyer_type').agg(value=('order_value','sum'),orders=('order_id','size'),rating=('review_score','mean'),
             late_rate=('late_flag','mean'),delivery_time=('delivery_time','mean'),freight_burden=('freight_burden','mean')).reset_index()
        # Attribute only selected item value while classifying full-history buyer behaviour.
        a['value']=a.buyer_type.map(f.groupby('buyer_type').item_value.sum()).fillna(0)
        share=100*a.loc[a.buyer_type.eq('Repeat buyer'),'value'].sum()/max(a.value.sum(),1)
        a['share']=100*a.value/max(a.value.sum(),1)
        fig=px.bar(a,x='share',y=['Selected value']*len(a),color='buyer_type',orientation='h',color_discrete_map=COLORS,
            labels={'share':'Share of gross order value (%)','y':''},custom_data=['value','orders'])
        drivers=a.set_index('buyer_type')[['rating','late_rate','delivery_time','freight_burden']].T
        drivers.loc[['late_rate','freight_burden']]*=100
        z=drivers.div(drivers.max(axis=1).replace(0,np.nan),axis=0)
        fig2=px.imshow(z,color_continuous_scale=['#EDF6F1',TEAL],aspect='auto',text_auto=False)
        fig2.update_traces(customdata=drivers.values,hovertemplate='%{y}<br>%{x}: %{customdata:.2f}<extra></extra>')
        first=o[o.lifetime_order_seq.eq(1)&o.mature_90d.astype('boolean').fillna(False)]
        r=first.groupby('delivery_status').agg(n=('order_id','size'),repeat_rate=('repeat_within_90d','mean')).reset_index()
        r=r[r.n.ge(min_n)];r['repeat_rate']=pd.to_numeric(r.repeat_rate)*100
        return result(f'Repeat buyers account for {pct(share)} of selected gross value. These are customers with 2+ delivered orders in the full observed history.',
          [('Who contributes value?',style(fig)),('Experience comparison · row-normalized colours',style(fig2)),
           ('First delivery experience and observed 90-day return',bar(r,'delivery_status','repeat_rate',horizontal=False))],a,
          'A repeat buyer has at least two delivered orders in the full saved history. Their first order also counts toward repeat-buyer value; the table’s is_repeat field marks only later orders. In the colour chart, point to a cell to see its value. Late deliveries and shipping as a share of item price are shown as percentages. The return chart only uses first purchases with 90 days of records afterward. It cannot tell us why a buyer came back.',
          'Protect first-order delivery reliability; validate retention interventions with a controlled experiment.')
    if n==2:
        eligible=o[o.late_flag.notna()]
        bins=[-np.inf,-15,-7,-1,0,3,7,14,30,np.inf]
        line,a=binned(eligible,'delay_days',bins=bins,min_n=min_n)
        d=f[f.late_flag.notna()].copy();d['delay_bucket']=pd.cut(d.delay_days,bins).astype('string')
        h=metrics(d,['category','delay_bucket'])
        a=a.sort_values('x') if not a.empty else a
        if len(a)>1:
            a['change']=a['mean'].diff();b=a.loc[a.change.idxmin()]
            insight=f'The largest adjacent-bin rating drop is {abs(b.change):.2f} stars on entering {b.bucket} days relative to the promise.' if b.change<0 else 'No adjacent eligible delay bins show a decrease in average rating in this selection.'
        else:insight='Too few eligible delay bins to identify a descriptive tipping point.'
        return result(insight,[('Satisfaction as the promise is missed · 95% mean CI',line),
           ('Does the pattern differ by category?',heat(h,'category','delay_bucket','rating',min_n,'reviews')),
           ('Does the pattern differ by customer state?',heat(metrics(d,['customer_state','delay_bucket']),'customer_state','delay_bucket','rating',min_n,'reviews'))],a,
           'Days are counted by calendar date: 0 means delivery on the promised date, and 3 means three days late. The chart groups orders by how early or late they arrived. The biggest rating drop can change when the groups, products or number of reviews change. It does not prove that one exact day causes bad reviews. The colour charts show up to 18 rows with the most orders.',
           'Escalate delivery exceptions before the promise is missed, then test category-specific alert thresholds.')
    if n==3:
        a=metrics(f,['category','customer_state'])
        # Local active supply is counted across destinations, keeping all other filters.
        supply=kwargs.get('supply_frame',f)
        local=supply.groupby(['category','seller_state']).seller_id.nunique()
        a['local_sellers']=[local.get((r.category,r.customer_state),0) for r in a.itertuples()]
        a['orders_per_local_seller']=a.orders/a.local_sellers.replace(0,np.nan)
        a['demand_pressure']=a.orders/(a.local_sellers+1)
        a['no_local_supply']=np.where(a.local_sellers.eq(0),'No observed local supply','Observed local supply')
        a=a[a.orders.ge(min_n)].sort_values(['local_sellers','orders'],ascending=[True,False])
        z=a[a.local_sellers.eq(0)]
        ins=f'{len(z):,} category–state combinations have at least {min_n} orders and no observed active seller in the same state.'
        return result(ins,[('Demand pressure · orders / (local sellers + 1)',heat(a,'category','customer_state','demand_pressure',min_n)),
            ('Demand versus active local sellers',scatter(a,'local_sellers','orders','value','no_local_supply','category',True))],a,
            'A local seller is a seller in the buyer’s state who sold the selected category during the selected dates, even if they shipped to another state. Other filters still apply. The colour chart divides orders by the number of local sellers plus 1, so places with no recorded local seller can still be shown. The table gives the real counts. No recorded local seller does not mean nobody sells there. These records show purchases, not everything people might want to buy.',
            'Prioritize seller recruitment where observed demand is substantial and local fulfilment is scarce; validate logistics economics before expanding.')
    if n==4:
        a=metrics(f,['seller_state','customer_state']);a['lane']=a.seller_state+' → '+a.customer_state
        a=a[a.deliveries.ge(min_n)]
        flagged=a[(a.freight_burden>a.freight_burden.median())&(a.delivery_time>a.delivery_time.median())]
        line,_=binned(o[o.late_flag.notna()],'distance','delivery_time',min_n=min_n)
        return result(f'{len(flagged):,} eligible lanes have both above-median freight burden and above-median delivery time in this selection.',
          [('Cost versus service · each bubble is a lane',scatter(a,'freight_burden','delivery_time','orders','late_rate','lane',True)),
           ('Distance versus freight burden',scatter(a,'distance','freight_burden','orders','rating','lane')),
           ('Delivery time across distance bands · 95% mean CI',line)],a.sort_values('late_count',ascending=False),
          'A delivery route runs from the seller’s state to the buyer’s state. Distance is the average straight-line distance between their postal areas, not the road distance. Shipping share means shipping charges divided by item prices. For example, R$10 shipping on R$100 of items is 10%. Cost per kilometre leaves out distances under 1 km. We do not have the delivery company’s costs, discounts, abandoned baskets or promised delivery options, so we cannot judge profit or fairness.',
          'Audit expensive, slow lanes by carrier and product mix. Freight paid alone cannot establish logistics profitability or fairness.')
    if n==5:
        a=metrics(f,'category');a=a[a.reviews.ge(min_n)].copy()
        benchmark=100*o.low_rating.mean();cut=a.value.median()
        risk=a[(a.value.ge(cut))&(a.low_rate.gt(benchmark))]
        exposed=risk.value.sum();total=f.item_value.sum()
        a['priority']=np.select([a.value.ge(cut)&a.low_rate.gt(benchmark),a.value.ge(cut),a.low_rate.le(benchmark)],
            ['Fix','Protect','Explore growth'],default='Investigate')
        return result(f'{money(exposed)} ({pct(100*exposed/max(total,1))}) sits in {len(risk)} high-value categories with above-benchmark low-rating shares.',
          [('Where value and experience conflict',scatter(a,'value','low_rate','orders','priority','category')),
           ('Category value concentration',pareto(a,'category','value'))],a.sort_values('value',ascending=False),
           f'High value means a category’s item and shipping total is at least {money(cut)}, the middle value among categories with enough reviews. A category is flagged when its share of low ratings is above {pct(benchmark)}, the share for all reviewed orders in this selection. Your chosen star limit decides what counts as a low rating. The flagged amount is the value of these purchases, not a prediction of money that will be lost.',
           'Fix service in economically significant categories before reducing catalogue breadth. Protect high-value categories with healthy satisfaction.')
    if n==6:
        a=metrics(f,'seller_id').sort_values('value',ascending=False)
        a['seller_revenue_share']=a.value/max(a.value.sum(),1)
        ranks=np.arange(1,len(a)+1)
        a['seller_revenue_bucket']=np.select([ranks<=max(1,math.ceil(len(a)*.01)),ranks<=max(1,math.ceil(len(a)*.1))],['Top 1%','Next 9%'],default='Remaining 90%')
        total=a.value.sum();k=max(1,math.ceil(len(a)*.1));share=100*a.head(k).value.sum()/max(total,1)
        cs=f.groupby(['category','seller_id']).item_value.sum().rename('value').reset_index()
        cs['share']=cs.value/cs.groupby('category').value.transform('sum')
        cs['sq']=cs.share.pow(2)*10000
        h=cs.groupby('category').agg(HHI=('sq','sum'),top_seller_share=('share','max')).reset_index()
        h=h.merge(metrics(f,'category')[['category','orders','value']],on='category');h=h[h.orders.ge(min_n)]
        h['dependent']=h.HHI.gt(2500);h['top_seller_share']*=100
        h['Exposure']=h.value*h.top_seller_share/100
        return result(f'The top 10% of sellers ({k:,} of {len(a):,}) account for {pct(share)} of selected value. {int(h.dependent.sum())} eligible categories exceed HHI 2,500.',
          [('How concentrated is seller value?',pareto(a,'seller_id','value')),
           ('Category seller concentration · HHI',bar(h,'category','HHI')),
           ('Category concentration heatmap',heat(h.assign(metric='HHI'),'category','metric','HHI'))],h.sort_values('HHI',ascending=False),
           'Each seller gets only the value of their own items and shipping, even when an order has several sellers. HHI is a score for how much sales depend on a few sellers: a higher score means more dependence, and 10,000 means one seller has all the value. This study flags scores above 2,500 as a reason to check backup sellers. That is a study rule, not a legal judgment.',
           'Develop backup supply in concentrated categories; account for replacement demand before interpreting exposure as lost revenue.')
    if n in [7,8,9]:return marketing_question(n,m,min_n)
    if n==10:
        a=o.groupby('value_band',observed=True).agg(orders=('order_id','size'),reviews=('review_score','count'),rating=('review_score','mean'),
            late_rate=('late_flag','mean'),delivery_time=('delivery_time','mean'),installments=('payment_installments','mean')).reset_index()
        a.late_rate*=100;a=a[a.orders.ge(min_n)]
        d=o[o.late_flag.notna()]
        fig=box_summary(d,'value_band','delivery_time')
        h=metrics(f,['category','value_band'])
        ins='Service is compared across fixed order-value bands; each order receives one rating and one delivery observation.'
        if o.loc[o.order_value.ge(600),'review_score'].count()>=min_n and o.loc[o.order_value.lt(150),'review_score'].count()>=min_n:
            ins=f'R$600+ orders average {o.loc[o.order_value.ge(600),"review_score"].mean():.2f}/5, versus {o.loc[o.order_value.lt(150),"review_score"].mean():.2f}/5 below R$150.'
        return result(ins,[('Delivery distributions by full order value',style(fig)),
            ('Experience gaps across categories',heat(h,'category','value_band','rating',min_n,'reviews')),
            ('Installments and order value',box_summary(o,'payment_installments','order_value'))],a,
            'Price groups use the full order total, even when you choose just one product category. Value totals elsewhere count only the selected items and their shipping. Each order has one review score and one delivery record. We do not have payment fees or the cost of the goods, so we cannot say whether paying in several parts earns more profit.',
            'Check high-value service gaps within categories before designing a premium-order service policy.')


def marketing_question(n,m,min_n):
    if m.empty:return result('No leads match the marketing filters.',[('No leads',empty())])
    a=m.groupby('origin').agg(leads=('mql_id','size'),wins=('converted','sum'),matched=('matched_seller','sum')).reset_index()
    a['conversion']=100*a.wins/a.leads
    a=a[a.leads.ge(min_n)]
    if n==7:
        # Wilson binomial interval, with denominators visible in hover and table.
        phat=a.conversion/100;z=1.96;den=1+z*z/a.leads
        center=(phat+z*z/(2*a.leads))/den;half=z*np.sqrt(phat*(1-phat)/a.leads+z*z/(4*a.leads*a.leads))/den
        a['ci_low']=100*(center-half);a['ci_high']=100*(center+half)
        fig=go.Figure(go.Funnel(y=['Marketing-qualified leads','Closed seller','Matched in e-commerce'],x=[len(m),m.converted.sum(),m.matched_seller.sum()],
                               marker_color=[BLUE,TEAL,GOLD],textinfo='value+percent initial'))
        rates=px.bar(a.sort_values('conversion'),x='conversion',y='origin',orientation='h',error_x=a.sort_values('conversion').ci_high-a.sort_values('conversion').conversion,
          error_x_minus=a.sort_values('conversion').conversion-a.sort_values('conversion').ci_low,hover_data=['leads','wins'],
          labels={'conversion':'Observed lead-to-win conversion (%)','origin':'Lead source'}) if not a.empty else empty()
        named=a[a.origin.ne('Unknown')]
        winner=named.sort_values('conversion',ascending=False).iloc[0] if len(named) else None
        ins=f'{int(m.converted.sum()):,} of {len(m):,} leads converted ({pct(100*m.converted.mean())}).'
        if winner is not None:ins+=f' {winner.origin} has the highest point estimate among named eligible sources: {pct(winner.conversion)} ({int(winner.wins)}/{int(winner.leads)}).'
        return result(ins,[('From lead to observed seller',style(fig)),('Source conversion · 95% Wilson CI',style(rates))],a,
           'A lead is a possible seller contacted by the sales team. The date filter uses their first contact, while a successful sign-up can be on any date in the records. Newer leads may have had less time to sign up. Unknown means the source was not recorded and stays in the totals. The lines beside the bars show how uncertain the rates are; overlapping ranges mean the highest bar may not be the best source. Matched means a seller ID also appears in the order-item records, not that we can see all of that seller’s business.',
           'Use conversion and uncertainty alongside downstream trading quality before moving acquisition budget. Marketing spend and CAC are unavailable.')
    wins=m[m.converted].copy()
    mature=wins[wins.mature_90d & wins.matched_seller].copy()
    if n==8:
        declared=wins[wins.declared_monthly_revenue.gt(0)]
        chart=style(px.box(declared,x='origin',y='declared_monthly_revenue',points='outliers',log_y=True,
            labels={'declared_monthly_revenue':'Positive declared monthly revenue (R$, log scale)','origin':'Lead source'})) if len(declared) else empty('No positive revenue declarations in this selection.')
        a=mature.groupby('origin').agg(sellers=('seller_id','nunique'),value_90d=('value_90d','median'),orders_90d=('orders_90d','median'),
                                    rating_90d=('rating_90d','mean')).reset_index()
        # Seller statistics require at least 5 sellers; the control is lead/order-specific.
        eligible=a[a.sellers.ge(5)]
        catalog=wins.dropna(subset=['declared_product_catalog_size'])
        catalog_chart=box_summary(catalog,'origin','declared_product_catalog_size',{'origin':'Lead source','declared_product_catalog_size':'Declared catalogue size'})
        ins=f'Only {len(declared):,} of {len(wins):,} closed sellers report positive monthly revenue. Commercial strength cannot be ranked reliably from declarations alone.'
        return result(ins,[('Declared scale · positive values only',chart),
           ('Matched mature sellers · median first-90-day performance',scatter(eligible,'orders_90d','value_90d','sellers','origin','origin',True)),
           ('Business profile of closed sellers',style(px.histogram(wins,x='origin',color='business_type',barmode='stack',labels=LABELS))),
           ('Catalogue-size declarations · sparse coverage',catalog_chart)],a,
           'Reported monthly sales of zero stay in the saved data but are left out of the sales-value chart. We do not know whether zero means no sales or missing information. The first-90-day sales chart only shows sources with at least 5 sellers linked to order records and 90 full days of records after sign-up. Sellers we cannot link are left out, so these results do not describe every seller. Seller counts for each source are shown in the table.',
           'Improve seller qualification data, then compare equal-age seller cohorts rather than raw totals or self-reported revenue.')
    a=mature.groupby('conversion_cohort',observed=True).agg(sellers=('seller_id','nunique'),value_90d=('value_90d','median'),
         orders_90d=('orders_90d','median'),rating_90d=('rating_90d','mean'),late_90d=('late_90d','mean')).reset_index()
    sc=scatter(mature,'conversion_days','value_90d',None,'origin','seller_id')
    lines=px.line(a,x='conversion_cohort',y='value_90d',markers=True,hover_data=['sellers'],labels=LABELS) if len(a) else empty()
    cx=scatter(mature[mature.reviews_90d.ge(5)],'conversion_days','rating_90d','reviews_90d','origin','seller_id')
    corr=mature[['conversion_days','value_90d']].corr(method='spearman').iloc[0,1] if len(mature)>2 else np.nan
    return result(f'{len(mature):,} matched sellers have a full 90-day observation window. Conversion speed versus 90-day value has Spearman ρ = {corr:.2f}.' if pd.notna(corr) else 'Insufficient mature matched sellers to assess conversion speed.',
        [('Conversion speed versus observed value',sc),('Equal-age cohort comparison',style(lines)),('Conversion speed versus customer experience',cx)],a,
        'The sales charts use sellers linked to order records with 90 full days of records after sign-up. Only purchases made from the sign-up day through day 89 that were delivered count; earlier purchases do not. Sellers we cannot link have an unknown source. Each seller has equal weight in the group’s average rating, and the rating chart requires at least 5 reviews per seller. A pattern between faster sign-up and higher sales does not show that one causes the other or predict future sales.',
        'Do not optimize sales-cycle speed alone. Track seller activation, equal-age trading value and customer outcomes together.')


def detail_question(n,o,f,m,min_n=30,scenario=50,top_n=10,**kwargs):
    """All 33 populated rows in the workbook's detailed-question sheet."""
    mapping={4:4,10:10,11:5,14:2,17:6,25:1,28:4,30:5,32:6}
    if n in mapping and n not in [14,32]:
        return final_question(mapping[n],o,f,m,min_n,scenario,top_n,**kwargs)
    if o.empty:return result('No orders match this selection.',[('No data',empty())])
    if n==1:
        a=metrics(f,'seller_id');a=a[a.deliveries.ge(min_n)]
        return result(f'The 10 sellers with the most late orders account for {number(a.nlargest(10,"late_count").late_count.sum())} late seller–order involvements.',
            [('Largest late-order volumes',bar(a,'seller_id','late_count')),('Separate scale from late rate',scatter(a,'orders','late_rate','late_count',None,'seller_id'))],a.sort_values('late_count',ascending=False),
            'A late order with two sellers is counted once for each seller. Adding seller counts can therefore count the same order twice. Having items in a late order does not prove that a seller caused the delay.')
    if n==2:
        a=metrics(f,'seller_id');a=a[a.reviews.ge(min_n)]
        b=metrics(f,'category');b=b[b.reviews.ge(min_n)]
        c=metrics(f,'customer_state');c=c[c.reviews.ge(min_n)]
        return result('Compare absolute one-star counts across sellers, categories and customer states.',
            [('One-star seller concentration',pareto(a,'seller_id','one_star')),('Categories with the most one-star experiences',bar(b,'category','one_star')),
             ('Customer regions with the most one-star experiences',bar(c,'customer_state','one_star'))],a.sort_values('one_star',ascending=False),
             'This page always counts reviews with exactly 1 star, even if you change the low-rating setting. An order with several sellers or product categories can appear in more than one group, so group counts may include the same order.')
    if n in [3,19]:
        a=metrics(f,['seller_state','customer_state']);a=a[a.orders.ge(min_n)]
        a['lane']=a.seller_state+' → '+a.customer_state
        d=f.drop_duplicates(['seller_state','customer_state','order_id']).copy()
        d['harm']=d.low_rating.eq(1)|d.late_flag.eq(1)
        harm=d.groupby(['seller_state','customer_state']).harm.sum().rename('harm_count').reset_index()
        a=a.merge(harm,on=['seller_state','customer_state'])
        return result('Lane-level views separate delivery time, satisfaction and the number of observed poor experiences.',
          [('Average delivery days',heat(a,'seller_state','customer_state','delivery_time',min_n)),
           ('Average review score',heat(a,'seller_state','customer_state','rating',min_n,'reviews')),
           ('Lanes with the most harm',bar(a,'lane','harm_count'))],a.sort_values('harm_count',ascending=False),
           'A route connects a seller state to a buyer state. Here, harm means an order arrived late or received a rating at or below your chosen star limit. An order with both problems counts only once on that route. Missing results do not count as known problems. These records do not show which delivery company was responsible.')
    if n==5:
        a=metrics(f,'category');a=a[a.orders.ge(min_n)]
        return result('Freight burden highlights categories where shipping consumes a large share of merchandise value.',
            [('Category freight / merchandise value',bar(a,'category','freight_burden')),
             ('Typical item shipping cost relative to price',style(px.box(f[f.category.isin(a.nlargest(10,'freight_burden').category)],
                x='category',y='freight_ratio',points=False,labels={'freight_ratio':'Item freight / price (ratio)','category':'Category'})))],a.sort_values('freight_burden',ascending=False),
             'The category bar divides total shipping charges by total item prices. For example, R$20 shipping on R$100 of items gives 20%. The other chart does this calculation for each item separately, so it shows how much the share varies between items.')
    if n in [6,7]:
        q=f[['product_weight_g','product_volume_cm3','freight_value','delivery_time','category','order_id']].dropna(subset=['product_weight_g','freight_value'])
        line,a=binned(q,'product_weight_g','freight_value',min_n=min_n)
        line2,b=binned(q,'product_volume_cm3','delivery_time',min_n=min_n)
        c=metrics(f,'category').merge(f.groupby('category').product_weight_g.mean(),on='category');c=c[c.orders.ge(min_n)]
        return result('Compare weight and size bands with freight and delivery outcomes, then use category filters to reduce product-mix differences.',
            [('Weight versus freight · binned mean and 95% CI',line),('Size versus delivery duration · binned mean',line2),
             ('Which categories combine weight and lateness?',scatter(c,'product_weight_g','late_rate','orders',None,'category'))],c,
             'The first two charts count each item separately. A three-item order repeats the same delivery result three times. The ranges around the averages do not account for this repetition, so they may look more certain than they are. Heavier or larger products may also use different delivery companies. These charts cannot tell which difference caused a delay.')
    if n==8:
        line,a=binned(o[o.late_flag.notna()],'processing_time','late_flag',bins=[0,1,2,3,5,7,14,30,np.inf],min_n=min_n)
        line.update_yaxes(tickformat='.0%',title='Late-delivery share')
        return result('Handling-time bands show whether slower seller handoff is associated with eventual lateness.',
          [('Seller handling versus late-delivery share',line),('Handling-time distribution by delivery outcome',style(px.box(o,x='delivery_status',y='processing_time',points=False,labels=LABELS)))],a,
          'Handling time runs from payment approval until the order is handed to the delivery company. Records where the end comes before the start are left out and listed under data-quality issues. When an order has several sellers, this shared time cannot tell us which seller caused a delay.')
    if n==9:
        d=o[o.late_flag.notna()].dropna(subset=['approval_time','processing_time','carrier_time'])
        d=d.melt(id_vars=['order_id'],value_vars=['approval_time','processing_time','carrier_time'],var_name='stage',value_name='days')
        a=d.groupby('stage').agg(mean_days=('days','mean'),median_days=('days','median'),orders=('order_id','nunique')).reset_index()
        winner=a.loc[a.mean_days.idxmax(),'stage'] if len(a) else 'unobserved'
        return result(f'{winner.replace("_"," ").title()} is the longest average stage among complete, chronologically valid delivered journeys.',
            [('Time spent at each stage',bar(a,'stage','mean_days',horizontal=False)),('Stage duration distributions',style(px.box(d,x='stage',y='days',points=False)))],a,
            'Only delivered orders with valid times for all three steps are included: payment approval, handoff to the delivery company, and delivery to the buyer. The average times add up to the average full journey. We do not have promised times for each step, so a long step does not necessarily mean someone missed a deadline.')
    if n==12:
        a=metrics(f,'category');a=a[a.reviews.ge(min_n)]
        return result('Review visibility and economic importance are distinct: compare reviewed-order counts with allocated gross value.',
          [('Review count versus value',scatter(a,'reviews','value','orders','rating','category')),
           ('Category rating versus value',scatter(a,'rating','value','reviews',None,'category'))],a.sort_values('value',ascending=False),
           'Review counts include only orders with a star rating. Each category gets the price and shipping of its own selected items. An order with items in two categories can count as a review for both. A high review count means more recorded feedback, not that the reviews were seen by more people.')
    if n==13:
        # Equal halves of the chosen observed time span, avoiding an arbitrary latest sparse month.
        split=o.order_purchase_timestamp.min()+(o.order_purchase_timestamp.max()-o.order_purchase_timestamp.min())/2
        a=metrics(f[f.order_purchase_timestamp.lt(split)],'seller_id')
        b=metrics(f[f.order_purchase_timestamp.ge(split)],'seller_id')
        d=a.merge(b,on='seller_id',suffixes=('_before','_after'))
        d=d[d.reviews_before.ge(min_n)&d.reviews_after.ge(min_n)].copy()
        d['rating_change']=d.rating_after-d.rating_before;d['late_change_pp']=d.late_rate_after-d.late_rate_before
        selected=d.nsmallest(5,'rating_change').seller_id
        h=metrics(f[f.seller_id.isin(selected)],['seller_id','month']);h=h[h.reviews.ge(min_n)]
        fig=px.line(h,x='month',y='rating',color='seller_id',markers=True,labels=LABELS) if len(h) else empty()
        fig.update_layout(showlegend=False)
        return result(f'Sellers are compared before and after {split.date()}, requiring at least {min_n} reviews in each half.',
            [('Scale versus rating change',scatter(d,'orders_after','rating_change','value_after','late_change_pp','seller_id',True)),
             ('Five largest rating declines · monthly evidence',style(fig))],d.sort_values('rating_change'),
             'The observed purchase dates are split into two equal time periods. Sellers need enough reviews in both periods to be compared. Months with too few reviews are left out of the line chart. Different products or holiday shopping can still change ratings, so a fall in ratings is a reason to investigate, not proof the seller got worse.')
    if n==14:return result('Compare the rating mix for early, on-date and late deliveries.',
        [('Rating distribution by promise adherence',rating_mix(o[o.delivery_status.ne('Unobserved')],'delivery_status'))],
        metrics(f,'delivery_status'), 'On time means delivered on the exact promised date. Orders delivered before that date are shown as early. Orders without a known delivery result are left out of this chart.')
    if n in [15,27]:
        d=f.drop_duplicates(['order_id','category'])
        a=d.groupby('category').agg(orders=('order_id','size'),installment_share=('installment_flag','mean'),
              avg_installments=('payment_installments','mean')).reset_index();a=a[a.orders.ge(min_n)];a.installment_share*=100
        return result('Installment use is associated with order value, but payment profitability cannot be calculated without fee and margin data.',
           [('Installment dependence by category',bar(a,'category','installment_share')),
            ('Full order value by installment count',style(px.box(o,x='payment_installments',y='order_value',points=False,labels=LABELS)))],a.sort_values('installment_share',ascending=False),
            'Paying in instalments means splitting a payment into parts. If an order has several payment records, we use the largest number of parts recorded. A payment-type filter includes an order if it used that type at all. We do not add an estimated payment fee, because the records do not give one.')
    if n==16:
        demand=f.drop_duplicates(['order_id','customer_state']).groupby('customer_state').size()
        supply=f.drop_duplicates(['order_id','seller_state']).groupby('seller_state').size()
        a=pd.concat([demand.rename('buyer_orders'),supply.rename('seller_orders')],axis=1).fillna(0).rename_axis('state').reset_index()
        a['seller_orders_negative']=-a.seller_orders
        fig=go.Figure();fig.add_bar(y=a.state,x=a.buyer_orders,orientation='h',name='Buyer orders',marker_color=TEAL)
        fig.add_bar(y=a.state,x=-a.seller_orders,orientation='h',name='Seller order involvements',marker_color=BLUE)
        fig.update_layout(barmode='relative',xaxis_title='Orders · supply shown to the left',yaxis_title='State',height=600)
        return result('Compare where orders originate with where sellers fulfil them.',[('Buyer and seller footprints',style(fig))],a,
            'An order with sellers in two states counts once for each seller state. The buyer’s state counts that order once. Seller-state totals can therefore be larger than the number of orders in the selection.')
    if n==18:
        a=metrics(f,'category');breadth=f.groupby('category').customer_state.nunique().rename('states_served')
        a=a.merge(breadth,on='category');a=a[a.orders.ge(min_n)];a['orders_per_seller']=a.orders/a.sellers
        return result('Find categories with broad observed geographic demand and relatively few active trading sellers.',
            [('Geographic breadth versus active seller count',scatter(a,'sellers','states_served','orders','orders_per_seller','category',True)),
             ('Demand per observed active seller',bar(a,'category','orders_per_seller'))],a.sort_values('orders_per_seller',ascending=False),
            'States served means the number of buyer states with purchases in this selection. Seller counts include only sellers with recorded sales, not everyone registered to sell. Orders per seller can help choose where to investigate, but cannot tell us how many more orders those sellers could handle.')
    if n==20:
        cols=['product_weight_g','product_volume_cm3','product_photos_qty','product_description_lenght','price','review_score']
        corr=f[cols].corr(method='spearman')
        fig=px.imshow(corr,zmin=-1,zmax=1,color_continuous_scale='RdBu',text_auto='.2f',aspect='auto')
        return result('Spearman correlation compares monotonic associations between product characteristics, price and order ratings.',
           [('Product and listing attribute associations',style(fig))],corr.reset_index(),
           'Each item counts separately. For each pair of measures, items missing either value are left out. Items in the same order share its rating, so that review may count several times. The score runs from −1 to 1: near 1 means the measures tend to rise together; near −1 means one tends to fall as the other rises. Different product types can affect the score. It does not tell us which product feature caused a rating.')
    if n==21:
        a,t=binned(f,'product_photos_qty',bins=[0,1,2,3,5,10,np.inf],min_n=min_n)
        b,u=binned(f,'product_description_lenght',min_n=min_n)
        return result('Compare listing richness with ratings within selected categories; do not interpret the pooled association as a listing-quality effect.',
            [('Photo count and average rating',a),('Description length and average rating',b)],t,
            'These charts group items by their photo count or description length and compare average order ratings. Items in the same order share a rating. The ranges around the averages do not account for shared ratings or repeated products, so they may look more certain than they are. More photos or longer text alone cannot be shown to cause better reviews.')
    if n==22:
        cols=['delay_days','processing_time','freight_value','product_weight_g','product_photos_qty','product_description_lenght']
        # Use one row per order, averaging product attributes within the selected items.
        d=f.groupby('order_id')[cols+['low_rating']].mean()
        a=pd.DataFrame({'factor':cols,'association':[d[[x,'low_rating']].corr(method='spearman').iloc[0,1] for x in cols],
                         'pairs':[len(d[[x,'low_rating']].dropna()) for x in cols]})
        a=a[a.pairs.ge(min_n)]
        return result('Compare unadjusted associations with low ratings, using one observation per order.',
           [('Operational and listing factors · Spearman ρ',bar(a,'factor','association'))],a,
           'Each order counts once. Product details, such as weight and photo count, are averaged across its selected items. Each comparison leaves out orders missing either value, so the number of orders can differ. A positive score means higher values tend to go with more low ratings; a negative score means fewer. This does not prove what caused a bad review or predict the next one.')
    if n==23:
        a=metrics(f,['category','seller_id','customer_state']);a=a[a.reviews.ge(min_n)]
        a=a[a.low_count.gt(0)].nlargest(40,'low_count')
        fig=px.treemap(a,path=['category','customer_state','seller_id'],values='low_count',color='low_rate',
             color_continuous_scale=['#F6E1C4',RED],labels=LABELS) if len(a) else empty()
        return result('Drill into the largest category, seller and customer-state combinations associated with low ratings.',
            [('Largest 40 eligible customer-experience hotspots',style(fig))],a,
            'The chart shows up to 40 groups with the most low-rated orders, among groups with enough reviews. A group combines category, seller and buyer state. An order with several sellers or categories can appear in several groups, so adding the blocks may count that order more than once.')
    if n==24:
        d=f.drop_duplicates(['seller_id','order_id']).copy();d['harm']=(d.low_rating.eq(1)|d.late_flag.eq(1)).astype(int)
        a=d.groupby('seller_id').agg(harm=('harm','sum'),orders=('order_id','size')).reset_index();a=a[a.orders.ge(min_n)]
        a=a[a.harm.gt(0)].sort_values('harm',ascending=False);k=max(1,math.ceil(len(a)*.1))
        share=100*a.head(k).harm.sum()/max(a.harm.sum(),1)
        return result(f'The top 10% of eligible sellers with observed harm ({k if len(a) else 0}) account for {pct(share)} of seller–order harm involvements.',
          [('Concentration of observed harm',pareto(a,'seller_id','harm'))],a,
          'Here, harm means late delivery or a rating at or below your chosen star limit. An order with both problems counts once per seller, but an order with two sellers can count for both. Only sellers with enough orders and at least one known problem enter the ranking. Missing results are not counted as known problems.')
    if n==26:
        d=f.drop_duplicates(['order_id','category','customer_state']);a=d.groupby(['category','customer_state']).size().rename('orders').reset_index()
        nat=a.groupby('category').orders.sum()/a.orders.sum();state=a.groupby('customer_state').orders.sum()
        a['state_category_share']=a.orders/a.customer_state.map(state)
        a['national_share']=a.category.map(nat);a['demand_index']=a.state_category_share/a.national_share
        a=a[a.orders.ge(min_n)]
        return result('An index below 1 means a category has a smaller share of observed category-order demand in that state than in the selected marketplace.',
          [('Category penetration index · 1 = selected-market mix',heat(a,'category','customer_state','demand_index',min_n,center=1))],a.sort_values('demand_index'),
          'An order with two product categories counts once in each category. The score compares a category’s share of orders in one state with its share in your whole selection, including any state filters. A score of 0.5 means half that share; 1 means the same share. A low score does not prove people want products they cannot buy.')
    if n==29:
        d=o.dropna(subset=['review_score']).copy()
        d['voice']=np.where(d.has_written_comment.astype('boolean').fillna(False),'Written comment','Stars only')
        a=d.groupby(['review_score','voice']).size().rename('orders').reset_index();a['share']=100*a.orders/a.groupby('review_score').orders.transform('sum')
        fig=px.bar(a,x='review_score',y='share',color='voice',labels={'share':'Reviewed orders (%)','review_score':'Star rating'},hover_data=['orders'])
        return result(f'{pct(100*d.has_written_comment.mean())} of selected reviewed orders include a written title or message.',
          [('Which ratings come with written feedback?',style(fig))],a,
          'Only orders with a star rating are included. A written comment means the saved review has a title or message. We do not check whether the words are positive or negative, and the records do not tell us whether the comment was published.')
    if n in [31,33]:return ramp(o,f,m,min_n,top_n)
    if n==32:
        a=metrics(f,'seller_id').sort_values('value',ascending=False);a['value_share']=100*a.value/max(a.value.sum(),1)
        exposed=a.head(top_n).value.sum();loss=exposed*scenario/100
        fig=go.Figure(go.Bar(x=['Selected baseline','Arithmetic exposure'],y=[a.value.sum(),loss],marker_color=[TEAL,RED]))
        return result(f'A {scenario}% reduction in the top {top_n} sellers’ selected value would expose {money(loss)}, assuming no replacement sales.',
          [('Seller concentration',pareto(a,'seller_id','value')),('User-controlled exposure scenario',style(fig))],a,
          'This is a what-if calculation. It reduces the selected top sellers’ item and shipping value by your chosen percentage. For example, a 50% setting removes half their value. It assumes buyers do not switch to other sellers and no seller replaces those sales. It is not a prediction.')
    raise ValueError(f'Unmapped detailed question: {n}')


def ramp(o,f,m,min_n=30,top_n=10):
    d=f[f.order_status.eq('delivered')].drop_duplicates(['seller_id','order_id']).sort_values(['order_purchase_timestamp','order_id']).copy()
    if d.empty:return result('No delivered seller orders in the selection.',[('No data',empty())])
    d['seq']=d.groupby('seller_id').cumcount()+1
    first=d.groupby('seller_id').order_purchase_timestamp.min()
    reach=d[d.seq.eq(top_n)].set_index('seller_id').order_purchase_timestamp
    a=first.rename('first_sale').to_frame().join(reach.rename('threshold_date'))
    a['days_to_threshold']=(a.threshold_date-a.first_sale).dt.total_seconds()/86400
    a['reached']=a.threshold_date.notna();a['seller_id']=a.index
    a['source_group']=np.where(a.seller_id.isin(m.loc[m.converted,'seller_id']),'Matched marketing seller','Source unknown / unmatched')
    d['age_days']=(d.order_purchase_timestamp-d.seller_id.map(first)).dt.total_seconds()/86400
    cutoff=o.order_purchase_timestamp.max();a['full_90d']=a.first_sale.add(pd.Timedelta(days=90)).le(cutoff)
    qualified=a[a.full_90d].index
    curves=[]
    for group,ids in a[a.index.isin(qualified)].groupby('source_group').groups.items():
        for day in [7,14,30,60,90]:
            counts=d[d.seller_id.isin(ids)&d.age_days.le(day)].groupby('seller_id').size().reindex(ids,fill_value=0)
            curves.append({'group':group,'day':day,'mean_orders':counts.mean(),'sellers':len(ids)})
    c=pd.DataFrame(curves)
    fig=px.line(c,x='day',y='mean_orders',color='group',markers=True,hover_data=['sellers'],labels={'day':'Days from first selected observed sale','mean_orders':'Mean cumulative orders'}) if len(c) else empty()
    return result(f'{int(a.reached.sum()):,} of {len(a):,} selected sellers reach {top_n} delivered orders during the selection.',
        [('Seller ramp · cohorts with 90 days observed',style(fig)),
         ('Time to volume · sellers that reached the threshold',style(px.box(a[a.reached],x='source_group',y='days_to_threshold',points=False)))],a.reset_index(drop=True),
        'Time starts at each seller’s first delivered purchase found within your filters, which may be later than their first real sale. Sellers not linked to marketing records have an unknown source. The time-to-target chart only includes sellers who reached your chosen order target; the table also lists those who did not. The lines only include sellers with 90 days of records afterward. All order filters apply.')
