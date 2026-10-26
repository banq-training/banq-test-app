/* Recipe: "Week skyline" (3D) for the Project Planner: a tower of tasks for every column, amber to do and green done.
 * Markup, after the board:  <section class="panel animate-in chart-panel"><h2>Your week in 3D</h2><div class="chart chart-stage" id="week-skyline" style="height: 380px"></div></section>
 * Script: also add <script src="js/vendor/echarts-gl.min.js"></script> after echarts.min.js; call drawWeekSkyline() as the last line of render().
 * Check: add a task on Thursday and an amber tower rises in the Thursday row; tick it and it turns green. */
function drawWeekSkyline() {
    const colors = Workshop.chartColors()
    const stage = Workshop.stage3D(document.getElementById('week-skyline').clientWidth > 700 ? 150 : 200)
    const rows = ['To do', 'Done']
    const data = state.columns.flatMap((column, x) => rows.map((row, y) => ({
        value: [x, y, state.items.filter(item => item.column === column && item.done === (row === 'Done')).length],
        itemStyle: { color: row === 'Done' ? colors.accent : colors.sun },
    }))).filter(point => point.value[2] > 0)
    Workshop.chart('#week-skyline', {
        tooltip: { formatter: item => `${echarts.format.encodeHTML(state.columns[item.value[0]])}, ${rows[item.value[1]]}: <b>${item.value[2]}</b>` },
        xAxis3D: { ...stage.axis, type: 'category', data: state.columns, name: '' },
        yAxis3D: { ...stage.axis, type: 'category', data: rows, name: '' },
        zAxis3D: { ...stage.axis, type: 'value', name: 'Tasks', minInterval: 1 },
        grid3D: { ...stage.grid3D, boxWidth: 170, boxDepth: 50, boxHeight: 60 },
        series: [{ type: 'bar3D', data, shading: 'lambert', bevelSize: 0.3, bevelSmoothness: 4 }],
    })
}
