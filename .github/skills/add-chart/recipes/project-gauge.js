/* Recipe: "Progress gauge" (flat) for the Project Planner: a big round dial that fills as tasks are ticked.
 * Markup, after the progress panel:  <section class="panel animate-in chart-panel"><h2>How far along</h2><div class="chart" id="progress-gauge" style="height: 280px"></div></section>
 * Script: call drawProgressGauge() as the last line of render().
 * Check: 4 tasks with 1 ticked reads 25%; tick one more and the dial sweeps to 50%. */
function drawProgressGauge() {
    const colors = Workshop.chartColors()
    const done = state.items.filter(item => item.done).length
    const percent = state.items.length ? Math.round((done / state.items.length) * 100) : 0
    Workshop.chart('#progress-gauge', {
        series: [{
            type: 'gauge', startAngle: 215, endAngle: -35, min: 0, max: 100, radius: '92%', center: ['50%', '58%'],
            progress: { show: true, roundCap: true, width: 22, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: colors.accent }, { offset: 1, color: colors.second }]) } },
            axisLine: { roundCap: true, lineStyle: { width: 22, color: [[1, colors.soft]] } },
            pointer: { show: false }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
            anchor: { show: false },
            title: { offsetCenter: [0, '34%'], fontSize: 15, color: colors.muted },
            detail: { offsetCenter: [0, '-2%'], fontSize: 40, fontWeight: 800, color: colors.ink, formatter: '{value}%' },
            data: [{ value: percent, name: `${done} of ${state.items.length} done` }],
        }],
    })
}
