import path from 'path';
import { fileURLToPath } from 'url';
import { refreshForecasts } from '../core/forecastUpdater.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dataDir = path.resolve(__dirname, '..', 'data');
const streamsDir = path.resolve(__dirname, '..', 'streams', 'live_forecasts');

const config = {
  quantum: {
    forecastPath: path.join(dataDir, 'quantum_weather_forecast_2025-10-15_to_2025-11-13.json'),
    feedPath: path.join(streamsDir, 'quantum_hourly_feed.json'),
  },
  bioLinear: {
    forecastPath: path.join(dataDir, 'bio_linear_disaster_outlook_2025-10-15_to_2025-11-13.json'),
    feedPath: path.join(streamsDir, 'bio_linear_hourly_feed.json'),
  },
};

refreshForecasts(config)
  .then((results) => {
    for (const result of results) {
      console.log(
        `${path.basename(result.forecastPath)} refreshed → ${result.firstDate} – ${result.lastDate} ` +
          `(added ${result.stats.added}, updated ${result.stats.updated}, skipped ${result.stats.skipped})`
      );
    }
    process.exit(0);
  })
  .catch((error) => {
    console.error('Forecast refresh failed', error);
    process.exit(1);
  });
