export class ChildSafetySystem {
  constructor() {
    this.boundaries = [];
    this.mentors = [];
    this.reports = [];
  }

  setBoundaries(boundaries) {
    this.boundaries = Array.isArray(boundaries) ? boundaries : [];
  }

  addMentor(name) {
    if (name) {
      this.mentors.push(name);
    }
  }

  detectHarmfulContent(text) {
    const redFlags = ['hurt', 'pain', 'abuse', 'violence'];
    const lower = text.toLowerCase();
    return redFlags.some(word => lower.includes(word));
  }

  monitorMessage(userId, message) {
    const harmful = this.detectHarmfulContent(message || '');
    const report = {
      userId,
      message,
      harmful,
      timestamp: Date.now()
    };
    this.reports.push(report);
    return report;
  }

  getReports() {
    return this.reports;
  }
}

export const childSafetySystem = new ChildSafetySystem();
