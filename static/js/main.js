document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    const message = form.getAttribute("data-confirm") || "Xác nhận thao tác?";
    if (!window.confirm(message)) {
      event.preventDefault();
    }
  });
});

document.querySelectorAll("form[data-method-choice]").forEach((form) => {
  const button = form.querySelector("button[type='submit']");
  const radios = form.querySelectorAll("input[name='processing_method']");

  const hasSelection = () => Array.from(radios).some((radio) => radio.checked);

  const updateButton = () => {
    button.disabled = !hasSelection();
  };

  radios.forEach((radio) => {
    radio.addEventListener("change", updateButton);
  });

  form.addEventListener("submit", (event) => {
    if (hasSelection()) {
      return;
    }

    event.preventDefault();
    window.alert("Vui lòng chọn phương thức xử lý");
  });

  updateButton();
});

document.querySelectorAll("[data-range-output]").forEach((input) => {
  const output = document.getElementById(input.dataset.rangeOutput);
  const updateOutput = () => {
    if (output) {
      output.textContent = input.value;
    }
  };

  input.addEventListener("input", updateOutput);
  updateOutput();
});

document.querySelectorAll("form").forEach((form) => {
  const signatureInput = form.querySelector("[data-signature-image-input]");
  const signaturePreview = form.querySelector("[data-signature-preview]");
  const signaturePreviewImage = signaturePreview ? signaturePreview.querySelector("img") : null;
  const keySelect = form.querySelector("[data-key-select]");
  const documentInput = form.querySelector("[data-document-file-input]");
  const documentPreviewText = form.querySelector("[data-document-preview-text]");
  const liveSignatureLayer = form.querySelector("[data-preview-signature-layer]");
  const liveSignatureImage = form.querySelector("[data-preview-signature-image]");
  const positionRadios = form.querySelectorAll("input[name='signature_position']");
  const offsetXInput = form.querySelector("[data-signature-offset-x]");
  const offsetYInput = form.querySelector("[data-signature-offset-y]");
  const widthInput = form.querySelector("[data-signature-width]");

  let uploadedSignatureUrl = "";
  let keySignatureUrl = "";

  const setSignaturePreview = (src) => {
    if (!signaturePreview || !signaturePreviewImage) {
      return;
    }

    if (!src) {
      signaturePreview.classList.remove("has-image");
      signaturePreviewImage.removeAttribute("src");
      if (liveSignatureImage) {
        liveSignatureImage.removeAttribute("src");
      }
      return;
    }

    signaturePreviewImage.src = src;
    signaturePreview.classList.add("has-image");
    if (liveSignatureImage) {
      liveSignatureImage.src = src;
    }
  };

  const currentPosition = () => {
    const selected = Array.from(positionRadios).find((radio) => radio.checked);
    return selected ? selected.value : "right";
  };

  const updateLiveSignaturePlacement = () => {
    if (!liveSignatureLayer || !liveSignatureImage) {
      return;
    }

    liveSignatureLayer.classList.remove("signature-left", "signature-center", "signature-right");
    liveSignatureLayer.classList.add(`signature-${currentPosition()}`);

    const offsetX = offsetXInput ? Number(offsetXInput.value || 0) : 0;
    const offsetY = offsetYInput ? Number(offsetYInput.value || 0) : 0;
    const width = widthInput ? Number(widthInput.value || 180) : 180;
    liveSignatureImage.style.width = `${width}px`;
    liveSignatureImage.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
  };

  if (keySelect) {
    const updateKeySignature = () => {
      const selectedOption = keySelect.options[keySelect.selectedIndex];
      keySignatureUrl = selectedOption ? selectedOption.dataset.signatureImageUrl || "" : "";
      if (!uploadedSignatureUrl) {
        setSignaturePreview(keySignatureUrl);
      }
    };

    keySelect.addEventListener("change", updateKeySignature);
    updateKeySignature();
  }

  if (signatureInput) {
    signatureInput.addEventListener("change", () => {
      const file = signatureInput.files && signatureInput.files[0];
      uploadedSignatureUrl = file ? URL.createObjectURL(file) : "";
      setSignaturePreview(uploadedSignatureUrl || keySignatureUrl);
      updateLiveSignaturePlacement();
    });
  }

  if (documentInput && documentPreviewText) {
    documentInput.addEventListener("change", () => {
      const file = documentInput.files && documentInput.files[0];
      if (!file) {
        documentPreviewText.textContent = "Chọn file .txt để xem trước nội dung tài liệu.";
        return;
      }

      const reader = new FileReader();
      reader.addEventListener("load", () => {
        documentPreviewText.textContent = reader.result || "";
      });
      reader.readAsText(file, "utf-8");
    });
  }

  positionRadios.forEach((radio) => {
    radio.addEventListener("change", updateLiveSignaturePlacement);
  });
  [offsetXInput, offsetYInput, widthInput].forEach((input) => {
    if (input) {
      input.addEventListener("input", updateLiveSignaturePlacement);
    }
  });

  updateLiveSignaturePlacement();
});

if (window.pdfjsLib) {
  window.pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js";
}

document.querySelectorAll("[data-pdf-placement]").forEach((panel) => {
  const form = panel.closest("form");
  const fileInput = form.querySelector("[data-pdf-file-input]");
  const canvas = panel.querySelector("[data-pdf-canvas]");
  const canvasWrap = panel.querySelector("[data-pdf-canvas-wrap]");
  const marker = panel.querySelector("[data-pdf-marker]");
  const handle = panel.querySelector("[data-pdf-resize-handle]");
  const prevButton = panel.querySelector("[data-pdf-prev]");
  const nextButton = panel.querySelector("[data-pdf-next]");
  const pageInput = panel.querySelector("[data-pdf-page-input]");
  const totalPages = panel.querySelector("[data-pdf-total]");
  const status = panel.querySelector("[data-pdf-status]");
  const hidden = {
    x: form.querySelector("[data-pdf-x]"),
    y: form.querySelector("[data-pdf-y]"),
    w: form.querySelector("[data-pdf-w]"),
    h: form.querySelector("[data-pdf-h]"),
    page: form.querySelector("[data-pdf-page]"),
  };

  if (!window.pdfjsLib || !fileInput || !canvas || !marker || !handle) {
    if (status) {
      status.textContent = "Khong tai duoc pdf.js, vui long kiem tra ket noi mang.";
    }
    return;
  }

  const context = canvas.getContext("2d");
  const state = {
    pdfDoc: null,
    pageNum: 1,
    scale: 1,
    canvasWidth: 0,
    canvasHeight: 0,
    markerLeft: 28,
    markerTop: 28,
    markerWidth: 220,
    markerHeight: 90,
  };

  const clamp = (value, min, max) => Math.max(min, Math.min(value, max));

  const saveData = () => {
    const centerX = state.markerLeft + state.markerWidth / 2;
    const centerY = state.markerTop + state.markerHeight / 2;
    const pdfX = Math.round(centerX / state.scale);
    const pdfY = Math.round((state.canvasHeight - centerY) / state.scale);
    const pdfW = Math.round(state.markerWidth / state.scale);
    const pdfH = Math.round(state.markerHeight / state.scale);

    hidden.x.value = pdfX;
    hidden.y.value = pdfY;
    hidden.w.value = pdfW;
    hidden.h.value = pdfH;
    hidden.page.value = state.pageNum;
    status.textContent = `Trang ${state.pageNum}: X=${pdfX}, Y=${pdfY}, kich thuoc ${pdfW}x${pdfH}`;
  };

  const updateMarker = () => {
    state.markerLeft = clamp(state.markerLeft, 0, Math.max(0, state.canvasWidth - state.markerWidth));
    state.markerTop = clamp(state.markerTop, 0, Math.max(0, state.canvasHeight - state.markerHeight));
    state.markerWidth = clamp(state.markerWidth, 50, Math.max(50, state.canvasWidth - state.markerLeft));
    state.markerHeight = clamp(state.markerHeight, 30, Math.max(30, state.canvasHeight - state.markerTop));

    marker.style.left = `${state.markerLeft}px`;
    marker.style.top = `${state.markerTop}px`;
    marker.style.width = `${state.markerWidth}px`;
    marker.style.height = `${state.markerHeight}px`;
    marker.style.display = "grid";

    const inside =
      state.markerLeft > 0 &&
      state.markerTop > 0 &&
      state.markerLeft + state.markerWidth < state.canvasWidth &&
      state.markerTop + state.markerHeight < state.canvasHeight;
    marker.classList.toggle("limit-hit", !inside);
    saveData();
  };

  const renderPage = (pageNumber) => {
    state.pdfDoc.getPage(pageNumber).then((page) => {
      const rawViewport = page.getViewport({ scale: 1 });
      const targetWidth = Math.min(760, Math.max(320, canvasWrap.parentElement.clientWidth - 24));
      state.scale = targetWidth / rawViewport.width;
      const viewport = page.getViewport({ scale: state.scale });

      state.canvasWidth = viewport.width;
      state.canvasHeight = viewport.height;
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      page.render({ canvasContext: context, viewport }).promise.then(() => {
        pageInput.value = pageNumber;
        hidden.page.value = pageNumber;
        totalPages.textContent = `/ ${state.pdfDoc.numPages}`;
        updateMarker();
      });
    });
  };

  const goToPage = (pageNumber) => {
    if (!state.pdfDoc) {
      return;
    }
    state.pageNum = clamp(pageNumber, 1, state.pdfDoc.numPages);
    renderPage(state.pageNum);
  };

  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      status.textContent = "Chon file PDF de bat dau dat vi tri chu ky.";
      return;
    }

    const reader = new FileReader();
    reader.addEventListener("load", () => {
      window.pdfjsLib.getDocument({ data: new Uint8Array(reader.result) }).promise.then((pdfDoc) => {
        state.pdfDoc = pdfDoc;
        state.pageNum = 1;
        state.markerLeft = 28;
        state.markerTop = 28;
        renderPage(1);
      }).catch(() => {
        status.textContent = "Khong doc duoc file PDF vua chon.";
      });
    });
    reader.readAsArrayBuffer(file);
  });

  canvas.addEventListener("mousedown", (event) => {
    const rect = canvas.getBoundingClientRect();
    state.markerLeft = event.clientX - rect.left - state.markerWidth / 2;
    state.markerTop = event.clientY - rect.top - state.markerHeight / 2;
    updateMarker();
  });

  let dragMode = "";
  let startX = 0;
  let startY = 0;
  let startLeft = 0;
  let startTop = 0;
  let startWidth = 0;
  let startHeight = 0;

  marker.addEventListener("mousedown", (event) => {
    if (event.target === handle) {
      return;
    }
    event.preventDefault();
    dragMode = "move";
    startX = event.clientX;
    startY = event.clientY;
    startLeft = state.markerLeft;
    startTop = state.markerTop;
  });

  handle.addEventListener("mousedown", (event) => {
    event.preventDefault();
    event.stopPropagation();
    dragMode = "resize";
    startX = event.clientX;
    startY = event.clientY;
    startWidth = state.markerWidth;
    startHeight = state.markerHeight;
  });

  document.addEventListener("mousemove", (event) => {
    if (!dragMode) {
      return;
    }

    if (dragMode === "move") {
      state.markerLeft = startLeft + event.clientX - startX;
      state.markerTop = startTop + event.clientY - startY;
    } else {
      state.markerWidth = startWidth + event.clientX - startX;
      state.markerHeight = startHeight + event.clientY - startY;
    }
    updateMarker();
  });

  document.addEventListener("mouseup", () => {
    dragMode = "";
  });

  prevButton.addEventListener("click", () => goToPage(state.pageNum - 1));
  nextButton.addEventListener("click", () => goToPage(state.pageNum + 1));
  pageInput.addEventListener("change", () => goToPage(Number(pageInput.value || 1)));
  pageInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }

    event.preventDefault();
    goToPage(Number(pageInput.value || 1));
  });
});
