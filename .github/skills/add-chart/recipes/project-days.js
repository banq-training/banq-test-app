/* Recipe: "Tasks per day" stacked bars (flat) for the Project Planner.
 * Markup, after the board:  <section class="panel animate-in chart-panel"><h2>Tasks per day</h2><div class="chart" id="day-chart"></div></section>
 * Script: call drawDayChart() as the last line of render().
 * Check: tick a task and its part of the bar changes from "To do" to "Done". */
function drawDayChart() {
    const colors = Workshop.chartColors()
    const count = (column, done) => state.items.filter(item => item.column === column && item.done === done).length
    Workshop.chart('#day-chart', {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: { top: 0, right: 0, data: ['Done', 'To do'] },
        grid: { top: 40, left: 4, right: 4, bottom: 4, containLabel: true },
        xAxis: { type: 'category', data: state.columns, axisTick: { show: false }, axisLine: { lineStyle: { color: colors.line } } },
        yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: colors.line, type: 'dashed' } } },
        series: [
            { name: 'Done', type: 'bar', stack: 'tasks', barWidth: '46%', data: state.columns.map(column => count(column, true)), itemStyle: { color: colors.accent } },
            { name: 'To do', type: 'bar', stack: 'tasks', data: state.columns.map(column => count(column, false)), itemStyle: { color: colors.second, opacity: 0.45, borderRadius: [8, 8, 0, 0] } },
        ],
    })
}
