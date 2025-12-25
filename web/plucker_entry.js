import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "Comfy.OutputPlucker",
  setup() {
    addFloatingButton();
  },
});

function addFloatingButton() {
  if (document.getElementById("plucker-floating-btn")) return;

  const btn = document.createElement("button");
  btn.id = "plucker-floating-btn";
  btn.textContent = "📂 Plucker";
  Object.assign(btn.style, {
    position: "fixed",
    top: "10px",
    right: "140px", // Next to the settings/queue buttons usually
    zIndex: "9000",
    backgroundColor: "#2a2a2a",
    color: "var(--p-100, #ffcc00)",
    border: "1px solid #444",
    borderRadius: "4px",
    padding: "4px 10px",
    cursor: "pointer",
    fontWeight: "bold",
    boxShadow: "0 2px 5px rgba(0,0,0,0.5)",
    fontSize: "14px",
  });

  btn.onmouseenter = () => (btn.style.backgroundColor = "#444");
  btn.onmouseleave = () => (btn.style.backgroundColor = "#2a2a2a");

  btn.onclick = () => showPluckerModal();
  document.body.appendChild(btn);
  console.log("‼️ Comfy.OutputPlucker: Floating button added.");
}

function showPluckerModal() {
  if (document.getElementById("plucker-modal")) return;


  const isAndroid = /Android/i.test(navigator.userAgent);

  const modal = document.createElement("div");
  modal.id = "plucker-modal";
  Object.assign(modal.style, {
    position: "fixed",
    top: "0",
    left: "0",
    width: "100vw",
    height: "100vh",
    backgroundColor: "rgba(0, 0, 0, 0.6)",
    zIndex: "10000",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backdropFilter: "blur(2px)",
  });

  const content = document.createElement("div");


  if (isAndroid) {
    // Fullscreen, no border radius, max size
    Object.assign(content.style, {
      width: "100%",
      height: "100%",
      backgroundColor: "#1e1e1e",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    });
  } else {
    // Desktop styling
    Object.assign(content.style, {
      width: "85%",
      height: "85%",
      backgroundColor: "#1e1e1e",
      borderRadius: "8px",
      display: "flex",
      flexDirection: "column",
      boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
      overflow: "hidden",
      border: "1px solid #444",
      position: "relative",
      minWidth: "400px",
      minHeight: "300px",
    });
  }

  const header = document.createElement("div");
  Object.assign(header.style, {
    padding: "10px 15px",
    backgroundColor: "#2a2a2a",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottom: "1px solid #333",
  });

  const title = document.createElement("span");
  title.textContent = "Output Plucker";
  title.style.color = "#ddd";
  title.style.fontWeight = "bold";
  title.style.fontFamily = "sans-serif";

  const closeBtn = document.createElement("button");
  closeBtn.textContent = "✕";
  Object.assign(closeBtn.style, {
    background: "transparent",
    border: "none",
    color: "#fff",
    fontSize: "18px",
    cursor: "pointer",
    padding: "0 5px",
    minWidth: "40px",
    minHeight: "40px"
  });

  closeBtn.onclick = () => modal.remove();
  header.appendChild(title);
  header.appendChild(closeBtn);

  const iframe = document.createElement("iframe");


  iframe.src = isAndroid ? "/plucker/mobile" : "/plucker/view";

  Object.assign(iframe.style, {
    flex: "1",
    width: "100%",
    border: "none",
    backgroundColor: "#1e1e1e",
  });



  if (!isAndroid) {
    const resizer = document.createElement("div");
    Object.assign(resizer.style, {
      width: "20px",
      height: "20px",
      position: "absolute",
      right: "0",
      bottom: "0",
      cursor: "nwse-resize",
      zIndex: "20",
      background: "linear-gradient(135deg, transparent 50%, #666 50%)", // Visual grip indicator
    });


    let isResizing = false;
    let startX, startY, startW, startH;

    resizer.onmousedown = (e) => {
      e.stopPropagation(); // Prevent modal click events
      isResizing = true;
      startX = e.clientX;
      startY = e.clientY;

      const rect = content.getBoundingClientRect();
      startW = rect.width;
      startH = rect.height;

      // IMPORTANT: Disable iframe pointer events while dragging so it doesn't swallow mouse moves
      iframe.style.pointerEvents = "none";

      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    };

    function onMouseMove(e) {
      if (!isResizing) return;
      const w = startW + (e.clientX - startX);
      const h = startH + (e.clientY - startY);
      content.style.width = `${w}px`;
      content.style.height = `${h}px`;
    }

    function onMouseUp() {
      isResizing = false;
      iframe.style.pointerEvents = "auto"; // Re-enable iframe interaction
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    }
    content.appendChild(resizer);
  }

  content.appendChild(header);
  content.appendChild(iframe);

  modal.appendChild(content);
  document.body.appendChild(modal);

  modal.onclick = (e) => {
    if (e.target === modal) modal.remove();
  };

  const escListener = (e) => {
    if (e.key === "Escape") {
      modal.remove();
      document.removeEventListener("keydown", escListener);
    }
  };
  document.addEventListener("keydown", escListener);
}