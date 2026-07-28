/**
 * plugin-click-order — jsPsych plugin for the Block 3 sequence-reconstruction test.
 *
 * Shows n images at once (already in randomized screen order) and asks the subject
 * to CLICK them in the order they think they occurred. Clicked images dim and get a
 * position badge; Backspace undoes the last click; the Continue button is enabled
 * only once every image has been placed.
 *
 * Mirrors psychopy_exp/experiment.py :: click_to_order so the two builds collect the
 * same data.
 *
 * Data:
 *   click_order — array of indices into `stimuli`, in the order clicked
 *   click_rts   — ms from trial onset for each click
 *   rt          — ms to the final Continue press
 */
var jsPsychClickOrder = (function (jspsych) {
  "use strict";

  const info = {
    name: "click-order",
    parameters: {
      stimuli:   { type: jspsych.ParameterType.STRING, array: true },   // image paths, screen order
      prompt:    { type: jspsych.ParameterType.HTML_STRING, default: "" },
      hint:      { type: jspsych.ParameterType.HTML_STRING, default: "" },
      button_label: { type: jspsych.ParameterType.STRING, default: "Continue" },
      assigned_opacity: { type: jspsych.ParameterType.FLOAT, default: 0.35 },
    },
  };

  class ClickOrderPlugin {
    constructor(jsPsych) { this.jsPsych = jsPsych; }

    trial(display_element, trial) {
      const n = trial.stimuli.length;
      const assigned = [];            // indices into trial.stimuli, in click order
      const rts = [];
      const start = performance.now();

      display_element.innerHTML = `
        <div class="co-wrap">
          <div class="co-prompt">${trial.prompt}</div>
          <div class="co-row">
            ${trial.stimuli.map((src, i) => `
              <div class="co-item" data-i="${i}">
                <img src="${src}" draggable="false">
                <div class="co-badge"></div>
              </div>`).join("")}
          </div>
          <div class="co-hint">${trial.hint}</div>
          <button class="co-btn" disabled>${trial.button_label}</button>
        </div>`;

      const items = Array.from(display_element.querySelectorAll(".co-item"));
      const btn = display_element.querySelector(".co-btn");

      const render = () => {
        items.forEach((el, i) => {
          const pos = assigned.indexOf(i);
          el.querySelector("img").style.opacity =
            pos === -1 ? 1 : trial.assigned_opacity;
          const badge = el.querySelector(".co-badge");
          badge.textContent = pos === -1 ? "" : String(pos + 1);
          badge.style.display = pos === -1 ? "none" : "flex";
        });
        btn.disabled = assigned.length !== n;
      };

      items.forEach((el, i) => {
        el.addEventListener("click", () => {
          if (assigned.includes(i)) return;         // already placed
          assigned.push(i);
          rts.push(Math.round(performance.now() - start));
          render();
        });
      });

      const onKey = (e) => {
        if (e.key === "Backspace" && assigned.length) {
          e.preventDefault();
          assigned.pop();
          rts.pop();
          render();
        }
      };
      document.addEventListener("keydown", onKey);

      const finish = () => {
        document.removeEventListener("keydown", onKey);
        display_element.innerHTML = "";
        this.jsPsych.finishTrial({
          click_order: assigned.slice(),
          click_rts: rts.slice(),
          rt: Math.round(performance.now() - start),
        });
      };
      btn.addEventListener("click", () => { if (!btn.disabled) finish(); });

      render();
    }
  }
  ClickOrderPlugin.info = info;
  return ClickOrderPlugin;
})(jsPsychModule);
