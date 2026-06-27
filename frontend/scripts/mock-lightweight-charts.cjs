const mockSeries = {
  setData: () => {},
  update: () => {},
  createPriceLine: () => ({ applyOptions: () => {} }),
  removePriceLine: () => {},
};
const mockMarkersApi = {
  setMarkers: () => {},
  markers: () => [],
  detach: () => {},
};
const mockChart = {
  addSeries: () => mockSeries,
  timeScale: () => ({
    setVisibleLogicalRange: () => {},
    scrollToRealTime: () => {},
    subscribeVisibleLogicalRangeChange: () => {},
  }),
  panes: () => [],
  resize: () => {},
  remove: () => {},
};
module.exports = {
  createChart: () => mockChart,
  CandlestickSeries: 'candlestick',
  AreaSeries: 'area',
  LineSeries: 'line',
  createSeriesMarkers: () => mockMarkersApi,
  LineStyle: { Dashed: 2, Solid: 0 },
};
