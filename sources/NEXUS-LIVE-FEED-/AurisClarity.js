const { harmodel } = require('./harmodel');

class AurisClarity {
  constructor() {
    this.model = harmodel;
  }

  async isClear(text) {
    const result = await this.model.classify(text);
    return result.results.some(r => r.match);
  }
}

module.exports = { AurisClarity };