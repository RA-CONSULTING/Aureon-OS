import test from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  combineBookTotals,
  equityReadingFromExchange,
  finiteOrNull,
  metricRingCaption,
  readingText,
  selectEquity,
  sumReadings,
} from './lib/reading.ts';
import { HUDMetricsPanel } from './components/cinema/HUDMetricsPanel.tsx';
import { MetricRingLegend } from './components/cinema/MetricRingLegend.tsx';
import { DuckCommandoIntel } from './components/warroom/DuckCommandoIntel.tsx';
import { ExchangeBalances } from './components/warroom/ExchangeBalances.tsx';
import { AmbientSoundscape } from './components/cinema/AmbientSoundscape.tsx';
import { QuickTrade } from './components/QuickTrade.tsx';

test('finite readings keep zero and withhold missing values', () => {
  assert.equal(finiteOrNull(null), null);
  assert.equal(finiteOrNull(undefined), null);
  assert.equal(finiteOrNull(''), null);
  assert.equal(finiteOrNull('nope'), null);
  assert.equal(finiteOrNull(0), 0);
  assert.equal(finiteOrNull('0'), 0);
  assert.equal(readingText(null), 'unavailable');
  assert.equal(readingText(0, (n) => n.toFixed(2)), '0.00');
  assert.equal(sumReadings([]), 0);
  assert.equal(sumReadings([null, 1]), null);
  assert.equal(sumReadings([0, 2]), 2);
});

test('exchange books do not turn a missing total into zero', () => {
  assert.equal(combineBookTotals(null, null), null);
  assert.equal(combineBookTotals(0, null), 0);
  assert.equal(combineBookTotals(null, 0), 0);
  assert.equal(combineBookTotals(1.5, 2), 3.5);
  assert.equal(selectEquity('', 0, 9), 0);
  assert.equal(selectEquity('', null, null), null);
  assert.equal(selectEquity('kraken unread', 0, 9), null);
  assert.equal(equityReadingFromExchange({
    truthStatus: 'no_data',
    generatedValues: false,
    totalEquityUsd: 0,
  }), null);
  assert.equal(equityReadingFromExchange({
    truthStatus: 'real_derived',
    generatedValues: false,
    totalEquityUsd: null,
  }), null);
  assert.equal(equityReadingFromExchange({
    truthStatus: 'real_derived',
    generatedValues: false,
    totalEquityUsd: 0,
  }), 0);
});

test('HUDMetricsPanel renders a null coherence as unavailable and keeps zero', () => {
  const missing = renderToStaticMarkup(
    <HUDMetricsPanel
      coherence={null}
      lambda={null}
      lighthouseSignal={null}
      prismState={null}
      hncFrequency={null}
      hncMarketState={null}
      gaiaLatticeState={null}
      gaiaFrequency={null}
      dominantNode={null}
    />,
  );
  assert.match(missing, /unavailable/);
  assert.doesNotMatch(missing, /0\.00/);
  assert.doesNotMatch(missing, /432/);

  const zero = renderToStaticMarkup(
    <HUDMetricsPanel
      coherence={0}
      lambda={0}
      lighthouseSignal={0}
      prismState="NEUTRAL"
      hncFrequency={0}
      hncMarketState="CONSOLIDATION"
      gaiaLatticeState="NEUTRAL"
      gaiaFrequency={0}
      dominantNode="Tiger"
    />,
  );
  assert.match(zero, /0\.00/);
  assert.match(zero, /HNC 0Hz/);
  assert.match(zero, /Gaia 0Hz/);
});

test('Metric ring legend renders a null equity as unavailable and hides when every ring is present', () => {
  const missing = renderToStaticMarkup(
    <MetricRingLegend
      totalEquity={null}
      coherence={null}
      totalTrades={null}
      winRate={null}
      totalPnl={null}
    />,
  );
  assert.match(missing, /equity, coherence, trades, win rate, pnl unavailable/);
  assert.equal(metricRingCaption([
    { name: 'equity', value: 0 },
    { name: 'coherence', value: 0 },
    { name: 'trades', value: 0 },
    { name: 'win rate', value: 0 },
    { name: 'pnl', value: 0 },
  ]), null);
  const zero = renderToStaticMarkup(
    <MetricRingLegend totalEquity={0} coherence={0} totalTrades={0} winRate={0} totalPnl={0} />,
  );
  assert.equal(zero, '');
});

test('QuickTrade renders a null balance and price as unavailable and keeps a zero balance', () => {
  const missing = renderToStaticMarkup(
    <QuickTrade
      canTrade
      initialSymbol="BTCUSDT"
      balances={[
        { asset: 'BTC', free: null, price: null, usdtValue: null },
        { asset: 'USDT', free: null, price: 1, usdtValue: null },
      ]}
    />,
  );
  assert.match(missing, /unavailable/);
  assert.doesNotMatch(missing, /\$0\.00/);
  assert.doesNotMatch(missing, /0\.000000 BTC/);

  const zero = renderToStaticMarkup(
    <QuickTrade
      canTrade
      initialSymbol="BTCUSDT"
      balances={[
        { asset: 'BTC', free: 0, price: 0, usdtValue: 0 },
        { asset: 'USDT', free: 0, price: 1, usdtValue: 0 },
      ]}
    />,
  );
  assert.match(zero, /0\.000000 BTC/);
  assert.match(zero, /\$0\.00/);
  assert.match(zero, /\$0\.00/);
});

test('DuckCommandoIntel renders a null pnl as unavailable and keeps zero', () => {
  const missing = renderToStaticMarkup(
    <DuckCommandoIntel
      showLore={false}
      exchangeStatuses={[{ exchange: 'kraken', connected: true, todayKills: 1, todayPnl: undefined, activePositions: undefined }]}
    />,
  );
  assert.match(missing, /unavailable/);
  assert.doesNotMatch(missing, /\$0\.00/);

  const zero = renderToStaticMarkup(
    <DuckCommandoIntel
      showLore={false}
      exchangeStatuses={[{ exchange: 'kraken', connected: true, todayKills: 0, todayPnl: 0, activePositions: 0 }]}
    />,
  );
  assert.match(zero, /\$0\.00/);
  assert.match(zero, />0</);
});

test('ExchangeBalances renders a null equity as unavailable and keeps zero', () => {
  const missing = renderToStaticMarkup(
    <ExchangeBalances
      totalEquityUsd={null}
      exchanges={[{ exchange: 'kraken', connected: true, totalUsdValue: null }]}
    />,
  );
  assert.match(missing, /unavailable/);
  assert.doesNotMatch(missing, /\$0\.00/);

  const zero = renderToStaticMarkup(
    <ExchangeBalances
      totalEquityUsd={0}
      exchanges={[{ exchange: 'kraken', connected: true, totalUsdValue: 0 }]}
    />,
  );
  assert.match(zero, /\$0\.00/);
});

test('AmbientSoundscape accepts a null coherence without rendering a zero reading', () => {
  const markup = renderToStaticMarkup(
    <AmbientSoundscape coherence={null} psi={null} fearLevel={null} gaiaFrequency={null} activeEvent={null} />,
  );
  assert.match(markup, /Enable Audio/);
  assert.doesNotMatch(markup, /unavailable|\$0\.00|0\.00/);
});
