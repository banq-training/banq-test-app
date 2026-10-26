/* Recipe: "How far from Palmer Square" bars (flat) for the Princeton Map: every place, nearest first.
 * Markup, after the places panel:  <section class="panel animate-in chart-panel"><h2>How far from Palmer Square</h2><div class="chart" id="distance-bars" style="height: 520px"></div></section>
 * Script: call drawDistances() as the last line of render().
 * Check: Nassau Hall shows 0.1 miles, the same as its place card says. */
function drawDistances() {
    const colors = Workshop.chartColors()
    const places = shown().map(place => ({ place, miles: Number(miles(place).toFixed(1)) })).sort((a, b) => a.miles - b.miles)
    Workshop.chart('#distance-bars', {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: value => `${value} miles` },
        grid: { top: 4, left: 4, right: 40, bottom: 4, containLabel: true },
        xAxis: { type: 'value', axisLabel: { formatter: '{value} mi' }, splitLine: { lineStyle: { color: colors.line, type: 'dashed' } } },
        yAxis: { type: 'category', inverse: true, data: places.map(entry => entry.place.name), axisTick: { show: false }, axisLine: { show: false } },
        series: [{
            type: 'bar', barWidth: '60%',
            data: places.map(entry => ({ value: entry.miles, itemStyle: { color: colorOf(entry.place), borderRadius: [0, 8, 8, 0] } })),
            label: { show: true, position: 'right', formatter: '{c} mi', color: colors.muted },
        }],
    })
}
