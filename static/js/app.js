(() => {
  const filters = JSON.parse(document.getElementById("filter-config").textContent);
  const $ = (selector) => document.querySelector(selector);
  const fileInput = $("#file-input");
  const dropzone = $("#dropzone");
  let imageId = null;
  let originalPreview = "";
  let outputUrl = null;
  let filename = "";
  let selectedFilter = "grayscale";
  let toastTimeout;

  function toast(message, error = false) {
    const el = $("#toast");
    el.textContent = message;
    el.classList.toggle("error", error);
    el.classList.add("show");
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => el.classList.remove("show"), 3200);
  }

  async function jsonResponse(response) {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Request failed.");
    return data;
  }

  function showImageState() {
    $("#empty-state").classList.add("hidden");
    $("#compare-view").classList.remove("hidden");
    $("#session-name").textContent = filename;
    $("#session-detail").textContent = "Ready to edit";
    $("#canvas-caption").textContent = filename;
    $("#apply-btn").disabled = false;
    $("#reset-btn").disabled = false;
  }

  function statsView(s) {
    $("#stats").innerHTML = [
      ["DIMENSIONS", `${s.width} × ${s.height}`, "Width × height"],
      ["DATA TYPE", s.dtype, `${s.channels} RGB channels`],
      ["PIXEL RANGE", `${s.min}–${s.max}`, "Minimum to maximum"],
      ["ARRAY MEMORY", `${s.memory_kb} KB`, `${s.mean} average intensity`]
    ].map(([label, value, help]) => `<div><label>${label}</label><strong>${value}</strong><small>${help}</small></div>`).join("");
    $("#dimensions").textContent = `${s.width} × ${s.height}`;
  }

  function histogramView(data) {
    const colors = {red:"#fa777d",green:"#83d9a0",blue:"#7da6ff"};
    const all = Object.values(data.channels).flat();
    const max = Math.max(...all, 1), width = 480, height = 80;
    const paths = Object.entries(data.channels).map(([channel, values]) => {
      const points = values.map((v, i) => `${i ? "L" : "M"} ${(i*width/(values.length-1)).toFixed(2)} ${(height-v/max*(height-5)).toFixed(2)}`).join(" ");
      return `<path d="${points}" fill="none" stroke="${colors[channel]}" stroke-width="1.7" vector-effect="non-scaling-stroke"/>`;
    }).join("");
    $("#histogram").innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="RGB histogram"><path d="M0 ${height-1} H${width}" stroke="#343a47" fill="none"/>${paths}</svg>`;
  }

  async function upload(file) {
    if (!file) return;
    if (file.size > 12 * 1024 * 1024) return toast("Image exceeds the 12 MB limit.", true);
    if (!file.type.startsWith("image/")) return toast("Choose a valid image file.", true);
    const form = new FormData();
    form.append("image", file);
    try {
      const data = await jsonResponse(await fetch("/api/upload", {method:"POST", body:form}));
      imageId = data.image_id;
      filename = data.filename;
      originalPreview = data.preview;
      outputUrl = null;
      $("#original-preview").src = originalPreview;
      $("#processed-preview").src = originalPreview;
      showImageState();
      statsView(data.stats);
      histogramView(data.histogram);
      $("#download-btn").disabled = true;
      $("#canvas-caption").textContent = `${filename} · Original loaded`;
      toast("Image loaded. Choose a filter to get started.");
    } catch (error) {
      toast(error.message, true);
    } finally {
      fileInput.value = "";
    }
  }

  function renderControls() {
    const controls = filters[selectedFilter].controls || [];
    if (!controls.length) {
      $("#controls").innerHTML = `<div class="control-empty">No adjustments needed for ${filters[selectedFilter].label.toLowerCase()}.</div>`;
      return;
    }
    $("#controls").innerHTML = controls.map(c => `
      <div class="range-control"><div class="range-head"><label for="control-${c.key}">${c.label}</label><output id="value-${c.key}">${c.default}${c.display || ""}</output></div>
      <input type="range" id="control-${c.key}" data-key="${c.key}" data-display="${c.display || ""}" min="${c.min}" max="${c.max}" step="${c.step}" value="${c.default}"></div>`).join("");
    $("#controls").querySelectorAll("input[type=range]").forEach(input => input.addEventListener("input", () => {
      $(`#value-${input.dataset.key}`).textContent = input.value + input.dataset.display;
    }));
  }

  async function apply() {
    if (!imageId) return toast("Upload an image first.", true);
    const params = {};
    $("#controls").querySelectorAll("input[type=range]").forEach(input => params[input.dataset.key] = Number(input.value));
    const button = $("#apply-btn");
    button.disabled = true;
    button.innerHTML = "<span>Processing…</span><b>◌</b>";
    try {
      const data = await jsonResponse(await fetch("/api/process", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({image_id:imageId, filter:selectedFilter, params})
      }));
      outputUrl = data.download_url;
      $("#processed-preview").src = data.preview;
      $("#download-btn").disabled = false;
      statsView(data.stats);
      histogramView(data.histogram);
      $("#canvas-caption").textContent = `${filename} · ${data.filter_label} applied`;
      $("#session-detail").textContent = `${data.filter_label} applied`;
      toast(`${data.filter_label} applied successfully.`);
    } catch (error) {
      toast(error.message, true);
    } finally {
      button.disabled = !imageId;
      button.innerHTML = "<span>Apply filter</span><b>→</b>";
    }
  }

  document.querySelectorAll(".filter-card").forEach(button => button.addEventListener("click", () => {
    selectedFilter = button.dataset.filter;
    document.querySelectorAll(".filter-card").forEach(card => card.classList.toggle("selected", card === button));
    renderControls();
  }));

  $("#browse-btn").addEventListener("click", event => { event.stopPropagation(); fileInput.click(); });
  $("#empty-upload").addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("click", event => { if (!event.target.closest("#browse-btn")) fileInput.click(); });
  dropzone.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); fileInput.click(); } });
  fileInput.addEventListener("change", () => upload(fileInput.files[0]));
  dropzone.addEventListener("dragover", event => { event.preventDefault(); dropzone.classList.add("drag"); });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
  dropzone.addEventListener("drop", event => { event.preventDefault(); dropzone.classList.remove("drag"); upload(event.dataTransfer.files[0]); });
  $("#apply-btn").addEventListener("click", apply);
  $("#reset-btn").addEventListener("click", () => {
    if (!originalPreview) return;
    outputUrl = null;
    $("#processed-preview").src = originalPreview;
    $("#download-btn").disabled = true;
    $("#session-detail").textContent = "Ready to edit";
    $("#canvas-caption").textContent = `${filename} · Original loaded`;
    toast("Preview reset to original.");
  });
  $("#download-btn").addEventListener("click", () => { if (outputUrl) window.location.href = outputUrl; });
  $("#fit-btn").addEventListener("click", () => toast("Both images are fitted to the preview."));
  $("#nav-analysis").addEventListener("click", () => document.querySelector(".bottom").scrollIntoView({behavior:"smooth",block:"center"}));
  $("#nav-editor").addEventListener("click", () => document.querySelector(".workspace").scrollIntoView({behavior:"smooth"}));
  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "o") { event.preventDefault(); fileInput.click(); }
  });
  renderControls();
})();