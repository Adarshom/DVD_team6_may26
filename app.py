"""Marketplace Observatory: a real, server-backed Plotly Dash application."""
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
from dash import Dash, html, dcc, dash_table, Input, Output, State, no_update, ctx
from analytics import load, filter_data, overview, final_question, detail_question, ROOT

#The initializing and bootstrapping script for Platoly Dash. 
# It loads the data, sets up the layout and callbacks, and runs the server.
ORDERS, ITEMS, MARKETING=load()
QUESTIONS=json.loads((ROOT/'docs/questions.json').read_text(encoding='utf-8'))
QUALITY=json.loads((ROOT/'data/processed/quality.json').read_text(encoding='utf-8'))
TITLES=['Repeat customers','Delivery tipping point','Demand and local supply','Freight and service',
        'Category priorities','Seller concentration','Lead conversion','Acquired seller quality','Speed to seller value','High-value experience']
DESCRIPTIONS=['Retention and the value of a second purchase','How a broken promise changes the review',
 'Where demand and seller presence diverge','What customers pay, and the service they receive',
 'Where customer experience has economic weight','How much value rests on a few sellers',
 'From qualified lead to closed seller','Commercial strength beyond lead volume',
 'Does a shorter sales cycle translate into better outcomes?','Does order value change the experience?']
START=str(ORDERS.order_purchase_timestamp.min().date());END=str(ORDERS.order_purchase_timestamp.max().date())
LEAD_START=str(MARKETING.first_contact_date.min().date());LEAD_END=str(MARKETING.first_contact_date.max().date())
#Plotly logo will show up, Abhinav can host it using gunicorn or other WSGI server, and it will be faster than the built-in Dash server. I have tested it on my PC, but it is slow due to low RAM and old CPU.
app=Dash(__name__,title='Marketplace Observatory | DVD Team 6',update_title='Updating analysis…',suppress_callback_exceptions=True)
server=app.server


def dropdown(id,options,placeholder,multi=True,value=None):
    options=[{'label':str(x),'value':x} for x in options]
    return dcc.Dropdown(id=id,options=options,value=value,multi=multi,placeholder=placeholder,
           clearable=multi,className='picker')


def field(label,child):return html.Div([html.Label(label),child],className='field')
def nav(label,value,small=''):
    return dcc.Link([html.Span(small,className='nav-number'),html.Span(label)],href='#'+value,refresh=False,className='nav-link',id='nav-'+value)


# Main page layout with sidebar navigation and content area, I have made the navbar collapsible, but the button is not on navbar, add comments here for your thoughts.
app.layout=html.Div([
 dcc.Location(id='url',refresh=False),dcc.Store(id='table-store'),dcc.Store(id='active-nav'),dcc.Download(id='download-data'),
 html.A('Skip to analysis',href='#main-content',className='skip-link'),
 html.Aside([
   html.Div([html.Div('M',className='brand-mark'),html.Div([html.Strong('MARKETPLACE'),html.Span('OBSERVATORY')])],className='brand'),
   nav('Executive overview','overview','◎'),
   html.Div('THE TEN QUESTIONS',className='nav-heading'),
   *[nav(t,f'q{k+1}',f'{k+1:02d}') for k,t in enumerate(TITLES)],
   html.Div('EXPLORE THE EVIDENCE',className='nav-heading'),
   nav('Detailed question lab','lab','↗'),nav('Data and methodology','methods','≡'),
 ],className='sidebar',id='sidebar'),
 html.Main([
   html.Button('☰ Hide navigation',id='sidebar-toggle',n_clicks=0,className='button secondary sidebar-toggle',
               **{'aria-controls':'sidebar','aria-expanded':'true'}),
   html.Header([html.H1(id='page-title'),html.P(id='page-subtitle',className='subtitle')],className='page-header'),
   html.Div(id='commerce-controls',children=[
     html.Div([
       field('Purchase dates',dcc.DatePickerRange(id='dates',start_date=START,end_date=END,min_date_allowed=START,max_date_allowed=END,display_format='DD MMM YY')),
       field('Product category',dropdown('categories',sorted(ITEMS.category.unique()),'All categories')),
       field('Customer state',dropdown('states',sorted(ORDERS.customer_state.unique()),'All states')),
       html.Button('Reset filters',id='reset',n_clicks=0,className='button secondary')
     ],className='filter-row'),
     html.Details([html.Summary('More filters and analysis settings'),html.Div([
       field('Order status',dropdown('statuses',sorted(ORDERS.order_status.unique()),'All statuses',value=['delivered'])),
       field('Seller state',dropdown('seller-states',sorted(ITEMS.seller_state.unique()),'All seller states')),
       field('Seller ID',dropdown('sellers',sorted(ITEMS.seller_id.unique()),'Search full seller ID')),
       field('Payment type · any used',dropdown('payments',['credit_card','boleto','voucher','debit_card','not_defined'],'All payment types')),
       field('Promise adherence',dropdown('delivery',['Early','On time','Late','Unobserved'],'All delivery outcomes')),
       field('Full order value',dropdown('values',['Under R$50','R$50–150','R$150–300','R$300–600','R$600+'],'All value bands')),
       field('Low rating means',dropdown('threshold',[1,2,3],'',multi=False,value=2)),
       field('Minimum observations per segment',dcc.Input(id='min-n',type='number',value=30,min=1,max=10000,step=1)),
       field('Top sellers / ramp-up order target',dcc.Input(id='top-n',type='number',value=10,min=1,max=1000,step=1)),
       field('Underperformance scenario (%)',dcc.Slider(id='scenario',min=0,max=100,step=5,value=50,marks={0:'0%',50:'50%',100:'100%'}))
     ],className='advanced-grid')],className='more-filters')
   ],className='filter-panel'),
   html.Div(id='marketing-controls',children=[
       html.Div([field('Lead first-contact dates',dcc.DatePickerRange(id='lead-dates',start_date=LEAD_START,end_date=LEAD_END,display_format='DD MMM YY')),
       field('Lead source',dropdown('origins',sorted(MARKETING.origin.unique()),'All lead sources')),
       field('Minimum leads per source',dcc.Input(id='min-leads',type='number',min=1,value=30))],className='filter-row'),
       html.P('Marketing pages use these lead filters. E-commerce filters do not apply. Downstream outcomes use each seller’s first 90 days after the win.',className='scope-note')
   ],className='filter-panel',style={'display':'none'}),
   html.Div(id='lab-controls',children=[field('Choose a detailed workbook question',dcc.Dropdown(id='detail-question',
       options=[{'label':f'{q["number"]:02d} · {q["question"]}','value':q['number']} for q in QUESTIONS['detailed']],value=1,clearable=False))],style={'display':'none'}),
   dcc.Loading(type='circle',color='#117B75',delay_show=200,children=html.Div(id='main-content')),
   #Added Everbody's name. Cheers guys.
   html.Footer('DVD TEAM 6 · MARKETPLACE OBSERVATORY · Adarshom · Abhinav · Aditya · Vian · Deveshu')
 ],className='main')
],className='shell',id='shell')


def clean_table(d):
    d=d.copy()
    for col in d:
        if isinstance(d[col].dtype,pd.CategoricalDtype):d[col]=d[col].astype(str)
        if pd.api.types.is_datetime64_any_dtype(d[col]):d[col]=d[col].dt.strftime('%Y-%m-%d')
        if pd.api.types.is_numeric_dtype(d[col]):d[col]=d[col].round(3)
    return json.loads(d.to_json(orient='records',date_format='iso'))

# Vian and Abhinav's methodology docs, Aditya and Deveshu's QA & data-quality metrics are combined. Abhinav can bug test this section
def method_content():
    checks=QUALITY['checks'];issues=QUALITY['issues']
    md=(ROOT/'docs/METHODOLOGY.md').read_text(encoding='utf-8') if (ROOT/'docs/METHODOLOGY.md').exists() else 'Methodology is being prepared.'
    rows=[{'check':k.replace('_',' ').title(),'result':'Passed' if v else 'FAILED'} for k,v in checks.items()]
    return html.Div([
      html.Div([html.H2('How to read this dashboard'),dcc.Markdown(md)],className='method-card'),
      html.Div([html.H2('Data reconciliation'),dash_table.DataTable(data=rows,columns=[{'name':x.title(),'id':x} for x in ['check','result']],
          style_cell={'textAlign':'left','padding':'12px','fontFamily':'Arial'},style_header={'fontWeight':'bold','backgroundColor':'#EFF4EF'})],className='method-card'),
      html.Div([html.H2('Observed data-quality issues'),html.Ul([html.Li(f'{k.replace("_"," ").capitalize()}: {v:,}') for k,v in issues.items()])],className='method-card')
    ])


# All filter inputs that trigger a page re-render (Aditya and Deveshu can add more inputs here if needed)
INPUTS=[Input('url','hash'),Input('dates','start_date'),Input('dates','end_date'),Input('categories','value'),Input('states','value'),
 Input('seller-states','value'),Input('sellers','value'),Input('statuses','value'),Input('payments','value'),Input('delivery','value'),
 Input('values','value'),Input('threshold','value'),Input('min-n','value'),Input('top-n','value'),Input('scenario','value'),
 Input('lead-dates','start_date'),Input('lead-dates','end_date'),Input('origins','value'),Input('min-leads','value'),Input('detail-question','value')]


# Central callback that rebuilds the page when any filter changes 
@app.callback(Output('page-title','children'),Output('page-subtitle','children'),Output('main-content','children'),
 Output('table-store','data'),Output('commerce-controls','style'),Output('marketing-controls','style'),Output('lab-controls','style'),*INPUTS)
def render_page(hash_value,start,end,categories,states,seller_states,sellers,statuses,payments,delivery,values,threshold,min_n,top_n,scenario,
                lead_start,lead_end,origins,min_leads,detail):
    page=(hash_value or '#overview').lstrip('#')
    if page=='methods':return 'Data and methodology','Definitions, joins, coverage and the limits of this study.',method_content(),[],{'display':'none'},{'display':'none'},{'display':'none'}
    n=int(page[1:]) if page.startswith('q') and page[1:].isdigit() and 1<=int(page[1:])<=10 else None
    min_n=max(1,int(min_n or 30));top_n=max(1,int(top_n or 10));threshold=int(threshold or 2)
    o,f=filter_data(ORDERS,ITEMS,start,end,categories,states,seller_states,sellers,statuses,payments,delivery,values,threshold)
    m=MARKETING.copy()
    if lead_start:m=m[m.first_contact_date.ge(pd.Timestamp(lead_start))]
    if lead_end:m=m[m.first_contact_date.lt(pd.Timestamp(lead_end)+pd.Timedelta(days=1))]
    if origins:m=m[m.origin.isin(origins)]
    marketing=n in [7,8,9]

    # Category-state supply considers other buyer destinations under the remaining filters.
    _,supply=filter_data(ORDERS,ITEMS,start,end,categories,None,seller_states,sellers,statuses,payments,delivery,values,threshold) if (n==3 or (page=='lab' and detail==18)) and states else (o,f)

    if n:
        title=TITLES[n-1];subtitle=DESCRIPTIONS[n-1];question=QUESTIONS['final'][n-1]['question']
        r=final_question(n,o,f,m,max(1,int(min_leads or 30)) if marketing else min_n,scenario or 0,top_n,supply_frame=supply)
    elif page=='lab':
        title='Detailed question lab';subtitle='Explore every populated question in the workbook.'
        question=QUESTIONS['detailed'][int(detail or 1)-1]['question']
        r=detail_question(int(detail or 1),o,f,MARKETING,min_n,scenario or 0,top_n,supply_frame=supply)
    else:
        title='Grow without breaking the experience.';subtitle='An integrated view of marketplace value, delivery and customer satisfaction.'
        question='Where should marketplace leadership invest, protect and intervene?';r=overview(o,f,min_n)
    if marketing:
        scope=f'{lead_start} to {lead_end} · {len(m):,} leads · {m.origin.nunique()} sources · historical observed outcomes'
    else:
        scope=f'{start} to {end} · {len(o):,} unique orders · {f.seller_id.nunique():,} sellers · minimum {min_n} observations per segment where applicable'
    rows=clean_table(r['table']);cols=[{'name':c.replace('_',' ').title(),'id':c} for c in r['table'].columns]
    table=html.Details([html.Summary(f'Inspect the evidence · {len(rows):,} rows'),
        html.Div([html.P('Sortable, searchable table. Download includes all rows in this filtered result.'),html.Button('Download evidence CSV',id='export',n_clicks=0,className='button secondary')],className='table-toolbar'),
        dash_table.DataTable(id='evidence-table',data=rows,columns=cols,page_size=12,sort_action='native',filter_action='native',
           style_table={'overflowX':'auto'},style_cell={'textAlign':'left','padding':'10px','fontFamily':'Arial','fontSize':'12px','minWidth':'110px','maxWidth':'320px','whiteSpace':'normal'},
           style_header={'fontWeight':'bold','backgroundColor':'#EFF4EF','color':'#223A39'},style_data_conditional=[{'if':{'row_index':'odd'},'backgroundColor':'#FAFBF8'}])
       ],className='evidence') if rows else html.Div()
    content=html.Div([
        html.Div(scope,className='scope-line'),
        html.Section([
            html.Div([html.H2('The question',className='eyebrow'),html.P(question)],className='summary-question'),
            html.Div([html.H2('What the selection shows',className='eyebrow'),html.P(r['insight'])],className='summary-insight'),
            html.Div([html.H2('Decision to consider',className='eyebrow'),html.P(r['action'] or 'Use these results to choose what to check next. Compare similar products, sellers or delivery routes before making changes.')],className='summary-action'),
            html.Div([html.H2('Interpretation and scope',className='eyebrow'),html.P(r['note'] or 'No orders or leads match these filters. Choose a wider date range or remove a filter to see results.')],className='summary-scope'),
        ],className='analysis-summary',**{'aria-label':'Question, findings, decision and scope'}),
        html.Div([html.Section([html.H3(name),dcc.Graph(figure=fig,responsive=True,id={'type':'chart','index':f"{page}_{idx}"},config={'displaylogo':False,'responsive':True,
          'toImageButtonOptions':{'format':'png','scale':2,'filename':'marketplace_chart'}})],
          className='chart-card chart-card-wide' if any(getattr(t,'type','')=='scattergeo' for t in fig.data) else 'chart-card') for idx,(name,fig) in enumerate(r['charts'])],className='chart-grid'),
        table])
    return title,subtitle,content,rows,{'display':'none' if marketing else 'block'},{'display':'block' if marketing else 'none'},{'display':'block' if page=='lab' else 'none'}


# Sends the currently visible evidence table as a CSV download
@app.callback(Output('download-data','data'),Input('export','n_clicks',allow_optional=True),State('table-store','data'),prevent_initial_call=True)
def export_data(clicks,rows):
    if not clicks or not rows:return no_update
    return dcc.send_data_frame(pd.DataFrame(rows).to_csv,'marketplace_evidence.csv',index=False)


@app.callback(Output('dates','start_date'),Output('dates','end_date'),Output('categories','value'),Output('states','value'),
 Output('seller-states','value'),Output('sellers','value'),Output('statuses','value'),Output('payments','value'),Output('delivery','value'),Output('values','value'),
 Output('threshold','value'),Output('min-n','value'),Output('top-n','value'),Output('scenario','value'),Input('reset','n_clicks'),prevent_initial_call=True)
def reset_filters(n):return START,END,[],[],[],[],['delivered'],[],[],[],2,30,10,50


app.clientside_callback("""function(clicks) {
 const collapsed = (clicks || 0) % 2 === 1;
 window.setTimeout(() => window.dispatchEvent(new Event('resize')), 0);
 return [collapsed ? 'shell sidebar-collapsed' : 'shell',
         collapsed ? '☰ Show navigation' : '☰ Hide navigation',
         collapsed ? 'false' : 'true'];
}""",Output('shell','className'),Output('sidebar-toggle','children'),
 Output('sidebar-toggle','aria-expanded'),Input('sidebar-toggle','n_clicks'))


app.clientside_callback("""function(hash) {
 const key = (hash || '#overview').slice(1);
 document.querySelectorAll('.nav-link').forEach(el => el.classList.toggle('active', el.id === 'nav-' + key));
 return window.dash_clientside.no_update;
}""",Output('active-nav','data'),Input('url','hash'))

#I have set it to debug=False, weird performance issue when set to true, but maybe it is due to low RAM and old CPU on my PC.
if __name__=='__main__':
    app.run(debug=False,host=os.getenv('HOST','127.0.0.1'),port=int(os.getenv('PORT','8050')))
