/* Recipe: "Busy days" calendar heatmap (flat) for the Calendar: every day of the month shown, darker when it holds more notes.
 * Markup, after the calendar panel:  <section class="panel animate-in chart-panel"><h2>Busy days</h2><div class="chart" id="busy-days" style="height: 300px"></div></section>
 * Script: call drawBusyDays() as the last line of render(), so it follows the month you are looking at.
 * Check: add two notes on one day and that square turns the darkest color. */
function drawBusyDays() {
    const colors = Workshop.chartColors()
    const pad = number => String(number).padStart(2, '0')
    const year = cursor.getFullYear()
    const month = cursor.getMonth()
    const last = new Date(year, month + 1, 0).getDate()
    const days = Array.from({ length: last }, (_, index) => `${year}-${pad(month + 1)}-${pad(index + 1)}`)
    const data = days.map(day => [day, state.items.filter(item => item.date === day).length])
    Workshop.chart('#busy-days', {
        tooltip: { formatter: item => `${item.value[0]}: <b>${item.value[1]} note${item.value[1] === 1 ? '' : 's'}</b>` },
        visualMap: { show: false, min: 0, max: Math.max(2, ...data.map(entry => entry[1])), inRange: { color: ['#eef3f1', colors.soft, colors.accent, colors.strong] } },
        calendar: {
            orient: 'vertical', range: `${year}-${pad(month + 1)}`, top: 40, bottom: 8, left: 'center', cellSize: [44, 'auto'],
            yearLabel: { show: false }, monthLabel: { show: false },
            dayLabel: { firstDay: 0, nameMap: ['S', 'M', 'T', 'W', 'T', 'F', 'S'], color: colors.muted, fontWeight: 700 },
            itemStyle: { borderWidth: 3, borderColor: colors.paper, color: colors.paper },
            splitLine: { show: false },
        },
        series: [{
            type: 'heatmap', coordinateSystem: 'calendar', data,
            itemStyle: { borderRadius: 8 },
            label: { show: true, formatter: item => Number(item.value[0].slice(8)), color: colors.ink, fontSize: 11 },
        }],
    })
}
