"use strict";

const PERSONA = "John Brown";
const WATERMARK = "SYNTHETIC TEST ONLY";

const courses = [
  {
    code: "GE-EHS-160",
    title: "Asbestos Awareness",
    fact: "If material may contain asbestos and is damaged, stop work, leave it undisturbed, and report it through the site process.",
    question: "What is the correct first response to damaged material that may contain asbestos?",
    options: ["Sweep it into a waste bag", "Leave it undisturbed and report it", "Break off a sample"],
    answer: 1
  },
  {
    code: "GE-EHS-180",
    title: "Compressed Gas Safety",
    fact: "Compressed-gas cylinders must be secured upright and moved only with an approved cylinder cart.",
    question: "How should a compressed-gas cylinder be stored and moved?",
    options: ["Secured upright and moved by approved cart", "Laid loose on the floor", "Rolled along its base"],
    answer: 0
  },
  {
    code: "GE-EHS-200",
    title: "Confined Space - Qualified Worker",
    fact: "A confined-space entry begins only after the permit, atmospheric test, attendant, and rescue arrangements are in place.",
    question: "Which conditions must exist before confined-space entry?",
    options: ["A flashlight and verbal permission", "A permit, atmospheric test, attendant, and rescue plan", "Only a mobile phone"],
    answer: 1
  },
  {
    code: "GE-EHS-237",
    title: "Defensive Driving",
    fact: "A defensive driver keeps a safe following distance and scans well ahead for changing hazards.",
    question: "Which behaviour best demonstrates defensive driving?",
    options: ["Following closely to stop overtaking", "Scanning ahead while keeping a safe gap", "Looking only at the vehicle in front"],
    answer: 1
  },
  {
    code: "GE-EHS-262",
    title: "EHS Overview for Field Services",
    fact: "Every worker has stop-work authority when an uncontrolled environmental, health, or safety risk is present.",
    question: "When may a field worker use stop-work authority?",
    options: ["Only after an injury", "When an uncontrolled EHS risk is present", "Only a manager may stop work"],
    answer: 1
  },
  {
    code: "GE-EHS-315",
    title: "Extreme Temperature Awareness",
    fact: "Heat or cold stress controls include suitable clothing, hydration, planned breaks, and monitoring coworkers for symptoms.",
    question: "Which set of controls reduces extreme-temperature risk?",
    options: ["Fewer breaks and heavier work", "Clothing, hydration, breaks, and coworker monitoring", "Working alone without reporting symptoms"],
    answer: 1
  },
  {
    code: "GE-EHS-320",
    title: "Fall Protection Advanced",
    fact: "Fall-arrest equipment must be inspected before use and connected to an approved anchorage.",
    question: "What must happen before using fall-arrest equipment?",
    options: ["Inspect it and use an approved anchorage", "Tie it to any nearby pipe", "Use it first and inspect it later"],
    answer: 0
  },
  {
    code: "GE-EHS-CEP-42",
    title: "Hazardous Waste Awareness",
    fact: "Hazardous waste stays in a compatible, closed, correctly labelled container within the designated accumulation area.",
    question: "How should hazardous waste be kept?",
    options: ["In an open unlabelled bucket", "Mixed with ordinary rubbish", "In a compatible closed labelled container"],
    answer: 2
  },
  {
    code: "GE-EHS-425",
    title: "Hexavalent Chromium Awareness",
    fact: "Tasks that can create hexavalent chromium exposure require the specified controls, hygiene, and respiratory protection assessment.",
    question: "What is required when a task can create hexavalent chromium exposure?",
    options: ["Specified controls, hygiene, and protection assessment", "Only opening a window", "No action if exposure is invisible"],
    answer: 0
  },
  {
    code: "GE-EHS-470",
    title: "Lead Safety Awareness",
    fact: "Lead-contaminated dust must not be dry swept; use the approved controlled cleaning method and wash before eating.",
    question: "Which action is correct around lead-contaminated dust?",
    options: ["Dry sweep it quickly", "Use approved controlled cleaning and wash before eating", "Blow it away with compressed air"],
    answer: 1
  },
  {
    code: "GE-EHS-CEP-34",
    title: "Lockout/Tagout Authorized",
    fact: "An authorized worker verifies zero energy after isolating, locking, tagging, and releasing stored energy.",
    question: "What follows isolation, lock, tag, and stored-energy release?",
    options: ["Immediate restart", "Verification of zero energy", "Removal of another worker's lock"],
    answer: 1
  },
  {
    code: "GE-EHS-530",
    title: "Occupational Noise Exposure Awareness",
    fact: "Where noise controls do not reduce exposure enough, use the specified hearing protection and remain in the hearing-conservation programme.",
    question: "What is required when noise controls are insufficient?",
    options: ["Specified hearing protection and conservation measures", "Cotton wool only", "Ignore noise if the task is short"],
    answer: 0
  },
  {
    code: "GE-EHS-465",
    title: "Overhead Cranes and Rigging",
    fact: "Never stand under a suspended load; inspect rigging and keep people outside the controlled lift area.",
    question: "Which rule applies to a suspended load?",
    options: ["Stand beneath it to guide it", "Keep people out and never stand beneath it", "Use damaged rigging for light loads"],
    answer: 1
  },
  {
    code: "GE-EHS-542",
    title: "Point of Work Risk Assessment Overview",
    fact: "A point-of-work risk assessment is updated when the task, location, people, equipment, or conditions change.",
    question: "When must the point-of-work risk assessment be revisited?",
    options: ["Only at the end of the week", "Whenever relevant task conditions change", "Only after an incident"],
    answer: 1
  },
  {
    code: "GE-EHS-545",
    title: "Portable Fire Extinguishers",
    fact: "Use an extinguisher only for a small incipient fire when trained, with the correct extinguisher and a clear escape route.",
    question: "When is extinguisher use appropriate?",
    options: ["For any fire regardless of size", "For a small early fire when trained and escape is clear", "When smoke blocks the exit"],
    answer: 1
  },
  {
    code: "GE-EHS-538",
    title: "Projects and Services EHS Plans",
    fact: "The project EHS plan identifies responsibilities, hazards, controls, communication, and emergency arrangements before work starts.",
    question: "What does a project EHS plan establish before work?",
    options: ["Responsibilities, hazards, controls, communication, and emergencies", "Only the commercial budget", "Only employee holiday dates"],
    answer: 0
  },
  {
    code: "GE-EHS-600",
    title: "Respiratory Protection Awareness",
    fact: "A respirator is used only after selection, medical evaluation, fit testing, training, and seal checks are complete.",
    question: "Which prerequisites apply before respirator use?",
    options: ["Selection, medical evaluation, fit test, training, and seal check", "Borrowing any available mask", "Facial hair improves the seal"],
    answer: 0
  },
  {
    code: "GE-EHS-640",
    title: "Safety Risk Assessment",
    fact: "Risk assessment considers severity and likelihood, then applies controls using the hierarchy before work proceeds.",
    question: "How is a safety risk controlled?",
    options: ["By considering severity and likelihood, then applying the hierarchy", "By accepting every risk", "By using PPE as the only possible control"],
    answer: 0
  },
  {
    code: "GE-EHS-620",
    title: "Scaffolding Awareness",
    fact: "Use scaffold only after a competent inspection and valid status tag; do not alter it unless authorized.",
    question: "What must be confirmed before using scaffold?",
    options: ["A competent inspection and valid status tag", "That no tag is visible", "That any worker has altered it"],
    answer: 0
  },
  {
    code: "GE-EHS-654",
    title: "Travel, Health, Safety, and Security Overview",
    fact: "Before travel, review destination risks, communications, medical needs, transport, and emergency contacts.",
    question: "What should be reviewed before work travel?",
    options: ["Only the hotel rating", "Destination risks, communications, medical needs, transport, and contacts", "Nothing if travel is domestic"],
    answer: 1
  },
  {
    code: "GE-EHS-670",
    title: "Welding, Cutting, and Brazing",
    fact: "Hot work begins only with authorization, fire prevention controls, suitable ventilation, and the required fire watch.",
    question: "Which controls are required before hot work begins?",
    options: ["Authorization, fire controls, ventilation, and required fire watch", "Only safety glasses", "A closed escape route"],
    answer: 0
  }
];

const screens = Array.from(document.querySelectorAll(".screen"));
const completed = new Set();
let activeCourse = null;
let selectedAnswer = null;
let lessonScrolled = false;

function showScreen(id) {
  for (const screen of screens) {
    screen.hidden = screen.id !== id;
  }
  document.body.dataset.screen = id;
  window.scrollTo({ top: 0, left: 0, behavior: "instant" });
}

function renderInbox() {
  const list = document.querySelector("#course-list");
  list.replaceChildren();
  for (const [index, course] of courses.entries()) {
    const row = document.createElement("div");
    row.className = `course-row${completed.has(course.code) ? " complete" : ""}`;
    const code = document.createElement("span");
    code.className = "course-code";
    code.textContent = course.code;
    const detail = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = `${index + 1}. ${course.title}`;
    const status = document.createElement("div");
    status.className = "course-status";
    status.textContent = completed.has(course.code) ? "Synthetic certificate downloaded" : "Assigned — not started";
    detail.append(title, status);
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = completed.has(course.code) ? "Completed" : "Open course";
    button.disabled = completed.has(course.code);
    button.addEventListener("click", () => openCourse(index));
    row.append(code, detail, button);
    list.append(row);
  }
  document.querySelector("#overall-progress").textContent = `${completed.size} of 21 complete`;
}

function openCourse(index) {
  activeCourse = courses[index];
  selectedAnswer = null;
  lessonScrolled = false;
  document.querySelector("#lesson-code").textContent = activeCourse.code;
  document.querySelector("#lesson-heading").textContent = activeCourse.title;
  const lessonCopy = document.querySelector("#lesson-copy");
  lessonCopy.replaceChildren();
  const blocks = [
    ["Recognise the hazard", `This synthetic module introduces the central field rule for ${activeCourse.title}. Pause before acting and identify the hazard in the current task.`],
    ["Apply the control", activeCourse.fact],
    ["Verify before proceeding", "Confirm the control is in place, communicate any change, and stop the task when the safe condition cannot be verified."]
  ];
  for (const [heading, copy] of blocks) {
    const block = document.createElement("section");
    block.className = "lesson-block";
    const h3 = document.createElement("h3");
    h3.textContent = heading;
    const paragraph = document.createElement("p");
    paragraph.textContent = copy;
    if (copy === activeCourse.fact) {
      paragraph.className = "lesson-fact";
    }
    block.append(h3, paragraph);
    lessonCopy.append(block);
  }
  document.querySelector("#begin-assessment").disabled = true;
  showScreen("lesson");
  updateScrollGate();
}

function updateScrollGate() {
  if (document.querySelector("#lesson").hidden || lessonScrolled) {
    return;
  }
  const sentinel = document.querySelector("#lesson-sentinel");
  if (sentinel.getBoundingClientRect().top < window.innerHeight - 20) {
    lessonScrolled = true;
    document.querySelector("#begin-assessment").disabled = false;
  }
}

function openAssessment() {
  if (!activeCourse || !lessonScrolled) {
    return;
  }
  selectedAnswer = null;
  document.querySelector("#question").textContent = activeCourse.question;
  document.querySelector("#assessment-feedback").textContent = "No answer submitted.";
  document.querySelector("#assessment-feedback").className = "feedback";
  document.querySelector("#submit-answer").disabled = true;
  const options = document.querySelector("#answer-options");
  options.replaceChildren();
  for (const [index, copy] of activeCourse.options.entries()) {
    const label = document.createElement("label");
    label.className = "answer-option";
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "synthetic-answer";
    radio.value = String(index);
    radio.dataset.textClass = "assessment_answer";
    radio.addEventListener("change", () => {
      selectedAnswer = index;
      document.querySelector("#submit-answer").disabled = false;
    });
    const text = document.createElement("span");
    text.textContent = `${String.fromCharCode(65 + index)}. ${copy}`;
    label.append(radio, text);
    options.append(label);
  }
  showScreen("assessment");
}

function submitAnswer() {
  if (!activeCourse || selectedAnswer === null) {
    return;
  }
  const feedback = document.querySelector("#assessment-feedback");
  if (selectedAnswer !== activeCourse.answer) {
    feedback.textContent = "Not correct. Re-read the visible lesson fact and try again.";
    feedback.className = "feedback error";
    return;
  }
  document.querySelector("#course-complete-heading").textContent = `${activeCourse.code} synthetic course complete`;
  document.querySelector("#download-status").textContent = "Certificate not yet downloaded.";
  document.querySelector("#return-inbox").disabled = true;
  showScreen("course-complete");
}

function pdfEscape(value) {
  return value.replaceAll("\\", "\\\\").replaceAll("(", "\\(").replaceAll(")", "\\)");
}

function buildSyntheticPDF(course) {
  const lines = [
    WATERMARK,
    "Aureon CourseOps 21 benchmark certificate",
    `Synthetic persona: ${PERSONA}`,
    `Course: ${course.code} - ${course.title}`,
    "No real-world qualification or provider validity"
  ];
  const textOps = lines.map((line, index) => `BT /F1 ${index === 0 ? 24 : 13} Tf 72 ${720 - index * 58} Td (${pdfEscape(line)}) Tj ET`).join("\n");
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
    `<< /Length ${textOps.length} >>\nstream\n${textOps}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  for (const [index, object] of objects.entries()) {
    offsets.push(pdf.length);
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  }
  const xref = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets.slice(1)) {
    pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return new Blob([pdf], { type: "application/pdf" });
}

function downloadCertificate() {
  if (!activeCourse) {
    return;
  }
  const blob = buildSyntheticPDF(activeCourse);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `SYNTHETIC-TEST-ONLY-${activeCourse.code}.pdf`;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  completed.add(activeCourse.code);
  document.querySelector("#download-status").textContent = `${WATERMARK} certificate generated for ${activeCourse.code}.`;
  document.querySelector("#return-inbox").disabled = false;
}

document.querySelector("#open-inbox").addEventListener("click", () => {
  renderInbox();
  showScreen("inbox");
});
window.addEventListener("scroll", updateScrollGate, { passive: true });
document.querySelector("#begin-assessment").addEventListener("click", openAssessment);
document.querySelector("#submit-answer").addEventListener("click", submitAnswer);
document.querySelector("#download-certificate").addEventListener("click", downloadCertificate);
document.querySelector("#return-inbox").addEventListener("click", () => {
  if (completed.size === courses.length) {
    showScreen("all-complete");
    return;
  }
  renderInbox();
  showScreen("inbox");
});
