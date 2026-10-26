/* Recipe: "Places by type" rose (flat) for the Princeton Map: a flower whose petals grow with the number of places of each type.
 * Markup, after the places panel:  <section class="panel animate-in chart-panel"><h2>Places by type</h2><div class="chart" id="type-rose" style="height: 320px"></div></section>
 * Script: call drawTypeRose() as the last line of render().
 * Check: History and Nature have the biggest petals (6 each); add a place and a "Mine" petal appears. */
function drawTypeRose() {
    const colors = Workshop.chartColors()
    const types = Object.keys(COLORS).filter(type => state.items.some(place => place.category === type))
    Workshop.chart('#type-rose', {
        tooltip: { formatter: item => `${item.name}: <b>${item.value} places</b>` },
        legend: { bottom: 0, icon: 'circle', itemGap: 14, textStyle: { color: colors.ink, fontWeight: 600 } },
        series: [{
            type: 'pie', roseType: 'radius', radius: ['16%', '80%'], center: ['50%', '45%'],
            itemStyle: { borderRadius: 10, borderColor: colors.paper, borderWidth: 3 },
            label: { position: 'inside', formatter: '{c}', color: '#ffffff', fontWeight: 800, fontSize: 15 },
            data: types.map(type => ({ name: type, value: state.items.filter(place => place.category === type).length, itemStyle: { color: COLORS[type] } })),
        }],
    })
}
