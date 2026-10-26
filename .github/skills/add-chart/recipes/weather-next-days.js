/* Recipe: "Next days" temperature chart (flat) for the Weather page: a warm line for highs, a cool line for lows, and a soft band between.
 * Markup, inside the weather panel after the forecast:  <div class="chart" id="next-days" style="height: 260px; margin-top: 1rem"></div>
 * Script: in show(), after `const weather = await fetchWeather(city)` and its notice, add drawNextDays(weather).
 * Check: point at Tomorrow: the high and low match tomorrow's forecast card. */
function drawNextDays(weather) {
    const colors = Workshop.chartColors()
    const days = weather.daily.map((day, index) => index === 0 ? 'Today'
        : weather.live ? new Date(`${day.date}T12:00`).toLocaleDateString(undefined, { weekday: 'short' }) : `Day ${index}`)
    const highs = weather.daily.map(day => Math.round(day.max))
    const lows = weather.daily.map(day => Math.round(day.min))
    Workshop.chart('#next-days', {
        tooltip: { trigger: 'axis', valueFormatter: value => `${value}\u00b0F` },
        legend: { top: 0, right: 0, data: ['High', 'Low'] },
        grid: { top: 36, left: 4, right: 12, bottom: 4, containLabel: true },
        xAxis: { type: 'category', boundaryGap: false, data: days, axisLine: { lineStyle: { color: colors.line } }, axisTick: { show: false } },
        yAxis: { type: 'value', scale: true, axisLabel: { formatter: '{value}\u00b0' }, splitLine: { lineStyle: { color: colors.line, type: 'dashed' } } },
        series: [
            { name: 'Low', type: 'line', data: lows, smooth: true, symbolSize: 9, lineStyle: { width: 3, color: colors.sky }, itemStyle: { color: colors.sky }, label: { show: true, position: 'bottom', formatter: '{c}\u00b0' } },
            {
                name: 'High', type: 'line', data: highs, smooth: true, symbolSize: 9, lineStyle: { width: 3, color: colors.coral }, itemStyle: { color: colors.coral },
                label: { show: true, position: 'top', formatter: '{c}\u00b0' },
                areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(228, 87, 46, 0.35)' }, { offset: 1, color: 'rgba(74, 163, 223, 0.05)' }]) },
            },
        ],
    })
}
