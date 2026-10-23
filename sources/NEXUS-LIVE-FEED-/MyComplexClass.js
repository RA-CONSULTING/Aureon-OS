  class MyComplexClass {
  constructor(data) {
    this.data = data;
  }

  process() {
    return this.data.map(item => item * 2);
  }
}

module.exports = { MyComplexClass };