import streamlit as st
import pandas as pd
import altair as alt
from numpy import where
import os

st.set_page_config(layout="wide")

@st.cache(persist=True)
def load_prep_data():
    df = pd.read_csv(os.path.join("data", "neow_sums.csv"))

    df.columns = ['Character', 'Bonus', 'Cost', 'Ascension', 'Win', 'Beat Heart', 'Immediate Abandon', 'N']
    bonus_mapping = {'Ten Percent Hp Bonus': '10% Max HP', 'Three Enemy Kill':'3 Combats 1 HP', 'Remove Card':'Remove Card',
        'Transform Card':'Transform Card', 'Upgrade Card':'Upgrade Card', 
        'Three Cards':'Choose Card',
        'One Random Rare Card':'Random Rare', 'Random Colorless': 'Random Colorless', 'Random Common Relic':'Common Relic',
        'Hundred Gold':'100 Gold', 'Three Small Potions':'3 Potions', 
        'Remove Two':'Remove 2', 'Transform Two Cards':'Transform 2', 'Two Fifty Gold':'250 Gold',
        'Three Rare Cards': 'Choose Rare',
        'Random Colorless 2':'2 Rand Colorless', 'One Rare Relic':'Rare Relic',
        'Twenty Percent Hp Bonus': '20% Max HP',
        'Boss Relic':'Boss Relic'}
    cost_mapping = {'No Gold':'No Gold', 'Percent Damage':'20% HP', 'None':'', 'Curse':'Curse', 'Ten Percent Hp Loss':'10% Max HP'}
    df = df.replace({'Bonus': bonus_mapping, 'Cost': cost_mapping})

    df['Bonus (Cost)'] = df.Bonus + where(df.Cost=='', '', ' (' + df.Cost + ')')

    df['Beat Act 3'] = df['Win'] - df['Beat Heart']

    df = df.drop(['Bonus', 'Cost'], axis=1)
    return df

df = load_prep_data()

# Sidebar with widgets
opt_char = st.sidebar.selectbox(
    'Character',['Ironclad', 'The Silent', 'Defect', 'Watcher'], 0)
    
opt_multi_asc = st.sidebar.radio('Ascension Levels', ['Single', 'Combine Levels'])
if opt_multi_asc == 'Single':
    opt_asc = st.sidebar.selectbox('Select Ascension Level', list(set(df['Ascension']))[::-1], 0)
    opt_asc_min, opt_asc_max = (opt_asc, opt_asc)
else:
    opt_asc_min, opt_asc_max = st.sidebar.slider("Select Ascension Level", 1, 20, (15, 20), 1)

opt_order = st.sidebar.selectbox(
    'Sort choices by', ['Alphabetic', 'Popularity', 'Winrate'], 2)

opt_distwin = st.sidebar.checkbox('Distinguish between beating Act 3 and beating the Heart', True)

opt_abandon = st.sidebar.checkbox('Show rate of runs that were abandoned before the first floor', False)

opt_scaling = st.sidebar.checkbox('Fix Scale', False)
if opt_scaling:
    scale_max = st.sidebar.select_slider("Max %", [.10,.15,.20,.30,.40,.50,1], .2,
    lambda d : "{:.0%}".format(d))

# Select data
df_sel = df[(df.Character==opt_char) & (df.Ascension>=opt_asc_min) & (df.Ascension<=opt_asc_max)]
df_sel = df_sel.drop(['Ascension'], axis=1)
df_sel = df_sel.groupby(['Character', 'Bonus (Cost)'], as_index=False).sum()

# Create summary statistics
agg_N = df_sel.groupby('Character').sum()
agg_N_N = agg_N['N'].tolist()[0] # need list for printing
agg_pc = agg_N / agg_N_N

# Transform data to longform
if opt_distwin:
    stack_vars = ['Beat Heart', 'Beat Act 3']
else:
    df_sel['Victory'] = df_sel['Win'] # duplicate used for melting
    stack_vars = ['Victory']

stack_vars = (stack_vars + ['Immediate Abandon']) if opt_abandon else stack_vars

df_sel = pd.melt(df_sel, id_vars=['Bonus (Cost)', 'Win', 'N'], value_vars=stack_vars, var_name='Result', value_name= 'Runs')
df_sel['percentage'] = df_sel['Runs'] / df_sel['N']
df_sel['Winrate'] = df_sel['Win'] / df_sel['N']

# Prepare Charts
df_sel['Runs_label'] = df_sel['Runs'].astype(str) + ' (' + df_sel['N'].astype(str) + ')'

graph_order = {'Alphabetic': 'Bonus (Cost)', 'Popularity': 'N', 'Winrate': 'Winrate'}[opt_order]
graph_order_direction = 'ascending' if (opt_order == 'Alphabetic') else 'descending'

highlight = alt.selection(type='single', on='mouseover', encodings=['y'])
barsScale = alt.Scale(domain=(0, scale_max)) if opt_scaling else alt.Scale()

# Barchart left
bars = alt.Chart(df_sel, title="Neow Choices and Outcomes").transform_calculate(
    Result_order="{'Beat Heart':0, 'Beat Act 3':1, 'Immediate Abandon':2}[datum.Result]").mark_bar().encode(
    x=alt.X('percentage:Q', scale=barsScale, axis=alt.Axis(format='%', title='')),
    y=alt.Y("Bonus (Cost):N", sort=alt.EncodingSortField(graph_order, order=graph_order_direction),
    axis=alt.Axis(title="Neow's Blessing (Cost)") ) ,
    fillOpacity=alt.condition(~highlight, alt.value(.75), alt.value(1)),
    color=alt.Color("Result", sort=alt.SortField("Result_order", "ascending"),legend=alt.Legend(orient="bottom", title="")),
    order='Result_order:O',
    tooltip=[alt.Tooltip('Runs_label', title="Runs"), 'Result', alt.Tooltip('percentage', format=".1%", title="")] #,title="none")] 
    ).add_selection(
    highlight).properties(width=300)

# Barchart right
cases = alt.Chart(df_sel, title = "Popularity").mark_bar().encode(
    x=alt.X('N:Q', axis=None),
    y=alt.Y("Bonus (Cost):N", sort=alt.EncodingSortField(graph_order, order=graph_order_direction), axis=None),#    tooltip=alt.Tooltip('N'),
    fillOpacity=alt.condition(~highlight, alt.value(.25), alt.value(1))).properties(width=150)

# Concat, display charts
altchart = alt.hconcat(bars, cases).configure_axis(
    labelFontSize=11,
    titleFontSize=13
).configure_title(fontSize=14).configure_legend(labelFontSize=11).configure_view(continuousWidth=450)
st.altair_chart(altchart, True)

# Print summary
fp = lambda s : "{:.1%}".format(s.tolist()[0])
st.write('<small>' + str(agg_N_N) + ' Runs: ' + 
    fp(agg_pc['Win']) + ' Average Winrate (' + 
    fp(agg_pc['Beat Heart']) + ' Heart beats)</small>', unsafe_allow_html=True)
