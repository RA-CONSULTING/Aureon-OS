
document.addEventListener('DOMContentLoaded', function () {
    const sealHarmonicsCtx = document.getElementById('sealHarmonicsChart').getContext('2d');

    const datasets = [
        {
            label: '222 Hz → 27.3 Hz x 8.1',
            data: [{x: 0, y: 0}, {x: 222, y: 27.3 * 8.1}],
            borderColor: 'orange',
            backgroundColor: 'orange',
            fill: false,
            tension: 0.1,
            pointRadius: 5
        },
        {
            label: '333 Hz → 20.8 Hz x 16.0',
            data: [{x: 0, y: 0}, {x: 333, y: 20.8 * 16.0}],
            borderColor: 'orangered',
            backgroundColor: 'orangered',
            fill: false,
            tension: 0.1,
            pointRadius: 5
        },
        {
            label: '444 Hz → 14.3 Hz x 31.0',
            data: [{x: 0, y: 0}, {x: 444, y: 14.3 * 31.0}],
            borderColor: 'crimson',
            backgroundColor: 'crimson',
            fill: false,
            tension: 0.1,
            pointRadius: 5
        },
        {
            label: '528 Hz → 14.3 Hz x 36.9',
            data: [{x: 0, y: 0}, {x: 528, y: 14.3 * 36.9}],
            borderColor: 'hotpink',
            backgroundColor: 'hotpink',
            fill: false,
            tension: 0.1,
            pointRadius: 5
        },
        {
            label: '783 Hz → 7.83 Hz x 100.0',
            data: [{x: 0, y: 0}, {x: 783, y: 7.83 * 100.0}],
            borderColor: 'deepskyblue',
            backgroundColor: 'deepskyblue',
            fill: false,
            tension: 0.1,
            pointRadius: 5
        },
        {
            label: '936 Hz → 20.8 Hz x 45.0',
            data: [{x: 0, y: 0}, {x: 936, y: 20.8 * 45.0}],
            borderColor: 'darkturquoise',
            backgroundColor: 'darkturquoise',
            fill: false,
            tension: 0.1,
            pointRadius: 5
        }
    ];

    new Chart(sealHarmonicsCtx, {
        type: 'line',
        data: {
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Seal Harmonics Mapped onto Earth Resonances',
                    font: {
                        size: 18
                    },
                    padding: {
                        bottom: 20
                    }
                },
                legend: {
                    position: 'right',
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    position: 'bottom',
                    title: {
                        display: true,
                        text: 'Frequency (Hz)'
                    },
                    grid: {
                        display: true,
                        drawOnChartArea: true,
                        drawTicks: true,
                        borderDash: [5, 5]
                    }
                },
                y: {
                    display: false,
                    beginAtZero: true
                }
            }
        }
    });
});
