"""Run: python -m unittest discover -s tests -v"""
import json
import math
import unittest
import numpy as np
import pandas as pd
from analytics import load,filter_data,metrics,final_question,detail_question,overview,ROOT
from prepare_data import haversine


class MarketplaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orders,cls.items,cls.marketing=load()
        cls.o,cls.f=filter_data(cls.orders,cls.items,statuses=['delivered'])

    def test_grain_and_source_reconciliation(self):
        self.assertEqual(len(self.orders),99441)
        self.assertEqual(len(self.items),112650)
        self.assertTrue(self.orders.order_id.is_unique)
        self.assertFalse(self.items.duplicated(['order_id','order_item_id']).any())
        self.assertAlmostEqual(self.orders.order_value.sum(),self.items.item_value.sum(),places=5)
        raw=pd.read_csv(ROOT/'data/raw/order_payments_dataset.csv')
        self.assertAlmostEqual(self.orders.payment_value.sum(),raw.payment_value.sum(),places=5)

    def test_multi_seller_revenue_is_not_duplicated(self):
        sums=metrics(self.f,'seller_id').value.sum()
        self.assertAlmostEqual(sums,self.f.item_value.sum(),places=5)
        cat=metrics(self.f,'category').value.sum()
        self.assertAlmostEqual(cat,self.f.item_value.sum(),places=5)
        multiple=self.orders[self.orders.seller_count.gt(1)].order_id.iloc[0]
        order=self.orders.set_index('order_id').loc[multiple]
        parts=self.items[self.items.order_id.eq(multiple)].groupby('seller_id').item_value.sum()
        self.assertAlmostEqual(parts.sum(),order.order_value)
        self.assertTrue((parts<order.order_value).all())

    def test_calendar_lateness_and_missing_denominators(self):
        same=self.o[self.o.delay_days.eq(0)&self.o.late_flag.notna()]
        self.assertGreater(len(same),0)
        self.assertTrue(same.late_flag.eq(0).all())
        self.assertTrue(self.orders.loc[self.orders.order_status.ne('delivered'),'late_flag'].isna().all())
        self.assertTrue(self.orders.loc[self.orders.review_score.isna(),'low_rating'].isna().all())
        for c in ['approval_time','processing_time','carrier_time','delivery_time']:
            self.assertTrue(self.orders[c].dropna().ge(0).all())

    def test_filters_recompute_exact_source_subset(self):
        o,f=filter_data(self.orders,self.items,start='2018-01-01',end='2018-01-31',
           categories=['Health Beauty'],states=['SP'],statuses=['delivered'],threshold=1)
        self.assertTrue(f.category.eq('Health Beauty').all())
        self.assertTrue(o.customer_state.eq('SP').all())
        self.assertTrue(o.order_purchase_timestamp.between('2018-01-01','2018-02-01',inclusive='left').all())
        self.assertEqual(set(o.order_id),set(f.order_id))
        self.assertAlmostEqual(o.low_rating.mean(),o.review_score.dropna().eq(1).mean())
        source=self.items[self.items.order_id.isin(o.order_id)&self.items.category.eq('Health Beauty')]
        self.assertAlmostEqual(source.item_value.sum(),f.item_value.sum())

    def test_repeat_definitions(self):
        self.assertTrue(self.o.loc[self.o.is_repeat,'lifetime_order_seq'].gt(1).all())
        customer=self.o.groupby('customer_unique_id').order_id.nunique()
        self.assertTrue(self.o.repeat_buyer.eq(self.o.customer_unique_id.map(customer).gt(1)).all())
        self.assertLess(self.o.is_repeat.sum(),self.o.repeat_buyer.sum())

    def test_marketing_and_observation_windows(self):
        self.assertEqual(len(self.marketing),8000)
        self.assertEqual(self.marketing.converted.sum(),842)
        self.assertEqual(self.marketing.matched_seller.sum(),380)
        mature=self.marketing[self.marketing.mature_90d]
        cutoff=self.o.order_purchase_timestamp.max()
        self.assertTrue((mature.won_date+pd.Timedelta(days=90)).le(cutoff).all())
        acquired=pd.read_parquet(ROOT/'data/processed/acquired_sales.parquet')
        post=acquired[acquired.days_after_won.between(0,90,inclusive='left')&acquired.order_status.eq('delivered')]
        self.assertAlmostEqual(post.item_value.sum(),self.marketing.value_90d.sum(),places=5)

    def test_haversine_units(self):
        self.assertAlmostEqual(float(haversine(0,0,0,1)),111.195,places=2)
        self.assertAlmostEqual(float(haversine(-23,-46,-23,-46)),0)
        self.assertTrue(self.items.distance.dropna().between(0,6000).all())

    def test_workbook_coverage_and_all_figures(self):
        questions=json.loads((ROOT/'docs/questions.json').read_text(encoding='utf-8'))
        self.assertEqual(len(questions['final']),10);self.assertEqual(len(questions['detailed']),33)
        for n in range(1,11):
            with self.subTest(final=n):
                r=final_question(n,self.o,self.f,self.marketing)
                self.assertTrue(r['insight'])
                for _,fig in r['charts']:json.loads(fig.to_json())
        for n in range(1,34):
            with self.subTest(detailed=n):
                r=detail_question(n,self.o,self.f,self.marketing)
                for _,fig in r['charts']:json.loads(fig.to_json())

    def test_empty_and_sparse_states(self):
        for kwargs in [dict(categories=['Missing category']),dict(categories=['Security And Services'],statuses=['delivered']),dict(statuses=['canceled'])]:
            o,f=filter_data(self.orders,self.items,**kwargs)
            for n in range(1,11):
                with self.subTest(kwargs=kwargs,final=n):final_question(n,o,f,self.marketing)
        empty=self.marketing.iloc[0:0]
        for n in [7,8,9]:
            self.assertIn('No leads',final_question(n,self.o,self.f,empty)['insight'])

    def test_http_callback_download_and_reset(self):
        from app import app,START,END,LEAD_START,LEAD_END,INPUTS,export_data,reset_filters
        c=app.server.test_client()
        for path in ['/','/_dash-layout','/_dash-dependencies']:
            self.assertEqual(c.get(path).status_code,200)
        key=next(k for k in app.callback_map if k.startswith('..page-title'))
        outs=[{'id':x.component_id,'property':x.component_property} for x in app.callback_map[key]['output']]
        vals=['#q5',START,END,['Health Beauty'],['SP'],None,None,['delivered'],None,None,None,2,30,10,50,LEAD_START,LEAD_END,None,30,1]
        inputs=[{'id':x.component_id,'property':x.component_property,'value':v} for x,v in zip(INPUTS,vals)]
        response=c.post('/_dash-update-component',json={'output':key,'outputs':outs,'inputs':inputs,'state':[],'changedPropIds':['url.hash']})
        self.assertEqual(response.status_code,200)
        data=response.get_json()['response'];rows=data['table-store']['data']
        self.assertEqual(rows[0]['category'],'Health Beauty')
        export=export_data(1,rows)
        self.assertIn('Health Beauty',export['content'])
        self.assertEqual(export['filename'],'marketplace_evidence.csv')
        reset=reset_filters(1)
        self.assertEqual(reset[6],['delivered']);self.assertEqual(reset[0],START)

    def test_methodology_uses_utf8(self):
        from app import method_content
        methodology=(ROOT/'docs/METHODOLOGY.md').read_bytes().decode('utf-8')
        self.assertIn('How the tables join',methodology)
        self.assertEqual(method_content().__class__.__name__,'Div')


if __name__=='__main__':unittest.main()
