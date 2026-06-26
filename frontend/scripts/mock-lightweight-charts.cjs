const mockSeries = {
  setData: () => {},
  update: () => {},
  createPriceLine: () => ({}),
  removePriceLine: () => {},
};
const mockChart = {
  addSeries: () => mockSeries,
  timeScale: () => ({ setVisibleLogicalRange: () => {} }),
  resize: () => {},
  remove: () => {},
};
module.exports = {
  createChart: () => mockChart,
  CandlestickSeries: 'candlestick',
  createSeriesMarkers: () => {},
  LineStyle: { Dashed: 2 },
};