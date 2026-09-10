"""Shared metric definitions and chart builders. All value measures are BRL."""
from pathlib import Path
import json
import math
import textwrap
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT=Path(__file__).resolve().parent
TEAL='#117B75'; RED='#C85646'; GOLD='#BC861F'; INK='#223A39'; BLUE='#6185AA'
PALETTE=[TEAL,RED,GOLD,BLUE,'#9387AE','#7F9B7C']
COLORS={'Early':TEAL,'On time':BLUE,'Late':RED,'Unobserved':'#9DA7A3',
        'No observed local supply':'#D62728','Observed local supply':'#1F77B4',
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
 'one_star':'One-star orders','low_count':'Low-rated orders','late_count':'Late orders',
 'repeat_rate':'Returned within 90 days (%)','delivery_status':'First delivery outcome',
 'local_sellers':'Local sellers'}

COMPACT_LABELS={'No observed local supply':'No local supply','Observed local supply':'Local supply',
 'Source unknown / unmatched':'Unknown source','Matched marketing seller':'Marketing seller',
 'Seller order involvements':'Seller orders','Gross order value (R$)':'Order value (R$)',
 'Low-rating share (%)':'Low ratings (%)','Late deliveries (%)':'Late orders (%)',
 'Orders / (local sellers + 1)':'Orders per<br>(local sellers + 1)'}


def compact_label(value):
    text=COMPACT_LABELS.get(value,value).replace('_',' ')
    return '<br>'.join(textwrap.fill(line,width=20,break_long_words=False,break_on_hyphens=False).replace('\n','<br>')
                      for line in text.split('<br>'))


# Load prepared parquet tables, rebuilding from CSVs if needed
def load():
    if not (ROOT/'data/processed/orders.parquet').exists():
        from prepare_data import prepare
        prepare()
    return tuple(pd.read_parquet(ROOT/'data/processed'/f'{x}.parquet') for x in ['orders','items','marketing'])


# Apply all user-selected filters to orders and items
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


# Compute standard KPIs grouped by one or more columns
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


# Apply consistent visual styling to every chart
def style(fig):
    for trace in fig.data:
        if trace.name:trace.name=compact_label(trace.name)
    color_title=fig.layout.coloraxis.colorbar.title.text
    fig.update_layout(template='plotly_white',paper_bgcolor='white',plot_bgcolor='white',
      font=dict(family='Arial, sans-serif',size=12,color=INK),margin=dict(l=24,r=24,t=55,b=55),
      legend=dict(orientation='h',y=1.02,yanchor='bottom',x=0,title_text='',font=dict(size=10)),height=365,
      coloraxis_colorbar=dict(thickness=10,len=.75,tickfont=dict(size=10),
          title=dict(text=compact_label(color_title) if color_title else '',side='top',font=dict(size=10))),hoverlabel=dict(bgcolor='white'),
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
        labels=LABELS,color_discrete_map=COLORS,color_continuous_scale=scale,hover_data={x:':,.2f',y:':,.2f'},
        category_orders={'no_local_supply':['Observed local supply','No observed local supply']})
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


# Brazilian state-to-region lookup for geographic filtering
REGION_MAP={'AC':'Norte','AM':'Norte','AP':'Norte','PA':'Norte','RO':'Norte','RR':'Norte','TO':'Norte',
    'AL':'Nordeste','BA':'Nordeste','CE':'Nordeste','MA':'Nordeste','PB':'Nordeste','PE':'Nordeste',
    'PI':'Nordeste','RN':'Nordeste','SE':'Nordeste','DF':'Centro-Oeste','GO':'Centro-Oeste',
    'MS':'Centro-Oeste','MT':'Centro-Oeste','ES':'Sudeste','MG':'Sudeste','RJ':'Sudeste','SP':'Sudeste',
    'PR':'Sul','RS':'Sul','SC':'Sul'}

#All, check if it is rendering properly, I wrote the code, but there are some pixel limits during rendering, so plotly vs OSM
def delivery_geo_map(o,f,region_filter=None):
    """Two-panel scatter map of Brazil: customers by delivery wait, sellers by volume."""
    delivered=o[o.order_status.eq('delivered')].dropna(subset=['delivery_time','customer_lat','customer_lon']).copy()
    delivered['region']=delivered.customer_state.map(REGION_MAP)
    if region_filter:
        delivered=delivered[delivered.region.isin(region_filter if isinstance(region_filter,list) else [region_filter])]
    # Aggregate customer locations by zip prefix for a cleaner plot
    cust=delivered.groupby('customer_zip_code_prefix').agg(
        lat=('customer_lat','first'),lon=('customer_lon','first'),
        median_delivery_days=('delivery_time','median'),orders=('order_id','size'),
        state=('customer_state','first'),city=('customer_city','first')).reset_index()
    cust['region']=cust.state.map(REGION_MAP)
    # Build seller layer from items table
    items_delivered=f[f.order_id.isin(delivered.order_id)].dropna(subset=['seller_lat','seller_lon']).copy()
    sellers=items_delivered.groupby('seller_id').agg(
        lat=('seller_lat','first'),lon=('seller_lon','first'),
        total_orders_volume=('order_id','nunique'),
        state=('seller_state','first'),city=('seller_city','first')).reset_index()
    sellers['region']=sellers.state.map(REGION_MAP)
    if region_filter:
        sellers=sellers[sellers.region.isin(region_filter if isinstance(region_filter,list) else [region_filter])]
    if cust.empty and sellers.empty:
        return empty('No geolocated deliveries in this selection.')
    fig=make_subplots(rows=1,cols=2,specs=[[{'type':'scattergeo'},{'type':'scattergeo'}]],
        subplot_titles=['Customer delivery time','Seller locations'],
        horizontal_spacing=0.02)
    # Left panel: customer locations colored by median delivery days
    fig.add_trace(go.Scattergeo(
        lat=cust.lat.tolist(),lon=cust.lon.tolist(),
        marker=dict(size=4,color=cust.median_delivery_days.tolist(),
            colorscale=[[0,'#2a9d2a'],[0.35,'#8cc63f'],[0.55,'#f0d048'],[0.75,'#e8832a'],[1.0,'#c83232']],
            cmin=cust.median_delivery_days.quantile(0.05) if len(cust) else 5,
            cmax=cust.median_delivery_days.quantile(0.95) if len(cust) else 25,
            colorbar=dict(title=dict(text='Median delivery<br>(days)',side='top',font=dict(size=10)),x=0.45,len=0.7,thickness=10,
                tickfont=dict(size=10)),
            line=dict(width=0)),
        text=(cust.city+', '+cust.state).tolist(),
        customdata=np.column_stack([cust.state,cust.region,cust.median_delivery_days.round(1),cust.orders]).tolist(),
        hovertemplate='<b>%{text}</b><br>Region: %{customdata[1]}<br>Median delivery: %{customdata[2]} days<br>Orders: %{customdata[3]}<extra>Customer</extra>',
        name='Customers',showlegend=True,
        legendgroup='customers'),row=1,col=1)
    # Right panel: seller locations sized by order volume
    size_ref=max(sellers.total_orders_volume.max()/35,1) if len(sellers) else 1
    fig.add_trace(go.Scattergeo(
        lat=sellers.lat.tolist(),lon=sellers.lon.tolist(),
        marker=dict(size=(np.clip(sellers.total_orders_volume/size_ref,3,35) if len(sellers) else []).tolist(),
            color='#8B1A4A',opacity=0.6,line=dict(width=0.3,color='#4A0A2A')),
        text=(sellers.city+', '+sellers.state).tolist(),
        customdata=np.column_stack([sellers.state,sellers.region,sellers.total_orders_volume]).tolist(),
        hovertemplate='<b>%{text}</b><br>Region: %{customdata[1]}<br>Total orders: %{customdata[2]}<extra>Seller</extra>',
        name='Sellers · order volume',showlegend=True,
        legendgroup='sellers'),row=1,col=2)
    # Shared geo settings for both panels
    geo_common=dict(scope='south america',showland=True,landcolor='#f5f4f0',
        showcoastlines=True,coastlinecolor='#c8c8c0',showframe=True,framecolor='#d0d0d0',
        showcountries=True,countrycolor='#c8c8c0',
        lonaxis=dict(range=[-75,-33]),lataxis=dict(range=[-35,6]),
        bgcolor='white',resolution=50)
    fig.update_geos(geo_common,row=1,col=1)
    fig.update_geos(geo_common,row=1,col=2)
    # Annotation A: the problem in the North/Northeast
    fig.add_annotation(x=0.12,y=0.92,xref='paper',yref='paper',
        text='<b>North and North East wait<br>two to three times longer</b>',showarrow=True,
        ax=30,ay=40,arrowcolor='#8B1A4A',arrowwidth=1.5,
        bordercolor='#8B1A4A',borderwidth=2,borderpad=6,bgcolor='rgba(255,255,255,0.92)',
        font=dict(size=11,color='#8B1A4A'))
    # Annotation B: seller concentration in Sao Paulo
    fig.add_annotation(x=0.88,y=0.28,xref='paper',yref='paper',
        text='<b>Sao Paulo state alone holds<br>60 percent of all sellers<br>and 42 percent of demand</b>',
        showarrow=True,ax=-30,ay=30,arrowcolor=INK,arrowwidth=1.5,
        bordercolor=INK,borderwidth=2,borderpad=6,bgcolor='rgba(255,255,255,0.92)',
        font=dict(size=11,color=INK))
    # Main title and subtitle
    fig.update_layout(
        title=dict(text='Delivery time and seller locations',
            x=0.01,y=0.98,font=dict(size=15,color=INK)),
        height=560,paper_bgcolor='white',plot_bgcolor='white',
        font=dict(family='Arial, sans-serif',size=12,color=INK),
        margin=dict(l=10,r=10,t=80,b=45),
        legend=dict(orientation='h',y=-0.02,x=0.5,xanchor='center',font=dict(size=11)),
        modebar_remove=['lasso2d','select2d'],
        # Source footnote
        annotations=list(fig.layout.annotations)+[dict(
            text=f'{len(delivered):,} delivered orders · {sellers.seller_id.nunique():,} sellers · {delivered.customer_state.nunique()} states',
            x=0.01,y=-0.06,xref='paper',yref='paper',showarrow=False,
            font=dict(size=10,color='#8A9A97'))])
    return fig


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


def final_question(n,o,f,m,min_n=30,**kwargs):
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
           ('Observed 90-day return to marketplace',bar(r,'delivery_status','repeat_rate',horizontal=False))],a,
          'A repeat buyer has at least two delivered orders in the full saved history. Their first order also counts toward repeat-buyer value. In the colour chart, point to a cell to see its value. Late deliveries and shipping as a share of item price are shown as percentages. The return chart only uses first purchases with 90 days of records afterward. It cannot tell us why a buyer came back.',
          'Protect first-order delivery reliability; validate retention interventions with a controlled experiment.')
    if n==2:
        eligible=o[o.late_flag.notna()]
        bins=[-np.inf,-15,-7,-1,0,3,7,14,30,np.inf]
        line,a=binned(eligible,'delay_days',bins=bins,min_n=min_n)
        delivery_chart,_=binned(o[o.order_status.eq('delivered')&o.delivery_time.ge(0)],'delivery_time',min_n=min_n)
        d=f[f.late_flag.notna()].copy();d['delay_bucket']=pd.cut(d.delay_days,bins).astype('string')
        h=metrics(d,['category','delay_bucket'])
        a=a.sort_values('x') if not a.empty else a
        if len(a)>1:
            a['change']=a['mean'].diff();b=a.loc[a.change.idxmin()]
            insight=f'The largest adjacent-bin rating drop is {abs(b.change):.2f} stars on entering {b.bucket} days relative to the promise.' if b.change<0 else 'No adjacent eligible delay bins show a decrease in average rating in this selection.'
        else:insight='Too few eligible delay bins to identify a descriptive tipping point.'
        return result(insight,[('Satisfaction as the promise is missed · 95% mean CI',line),
           ('Delivery time versus rating · 95% mean CI',delivery_chart),
           ('Does the pattern differ by category?',heat(h,'category','delay_bucket','rating',min_n,'reviews')),
           ('Does the pattern differ by customer state?',heat(metrics(d,['customer_state','delay_bucket']),'customer_state','delay_bucket','rating',min_n,'reviews'))],a,
           'Days relative to the promise are counted by calendar date: 0 means on time, and 3 means three days late. The delivery-time chart groups reviewed, delivered orders into up to eight duration bands, showing median days from purchase to delivery against average rating, with 95% mean confidence intervals. Bands below the minimum sample are omitted. The biggest rating drop can change with the groups, products or reviews selected; it does not establish causation. The colour charts show up to 18 rows with the most orders.',
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
        geo_chart=delivery_geo_map(o,f)
        return result(ins,[('Delivery geography of Brazil',geo_chart),
            ('Demand pressure · orders / (local sellers + 1)',heat(a,'category','customer_state','demand_pressure',min_n)),
            ('Demand versus active local sellers',scatter(a,'local_sellers','orders','value','no_local_supply','category',True))],a,
            'A local seller is a seller in the buyer’s state who sold the selected category during the selected dates, even if they shipped to another state. Other filters still apply. The colour chart divides orders by the number of local sellers plus 1, so places with no recorded local seller can still be shown. No recorded local seller does not mean nobody sells there. These records show purchases, not everything people might want to buy.',
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
           ('Category seller concentration · HHI',bar(h,'category','HHI'))],h.sort_values('HHI',ascending=False),
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
            ('Experience gaps across categories',heat(h,'category','value_band','rating',min_n,'reviews'))],a,
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
           'Reported monthly sales of zero stay in the saved data but are left out of the sales-value chart. We do not know whether zero means no sales or missing information. The first-90-day sales chart only shows sources with at least 5 sellers linked to order records and 90 full days of records after sign-up. Sellers we cannot link are left out, so these results do not describe every seller. ',
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
