import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "Comfy.OutputPlucker",
  setup() {
    // ‼️ Changed: Immediately add the floating button, skipping menu checks
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
    color: "var(--p-100, #ffcc00)", // ‼️ Use ComfyUI variable if avail, else fallback
    border: "1px solid #444",
    borderRadius: "4px",
    padding: "4px 10px",
    cursor: "pointer",
    fontWeight: "bold",
    boxShadow: "0 2px 5px rgba(0,0,0,0.5)",
    fontSize: "14px"
  });

  // ‼️ Hover effect for better visibility
  btn.onmouseenter = () => btn.style.backgroundColor = "#444";
  btn.onmouseleave = () => btn.style.backgroundColor = "#2a2a2a";

  btn.onclick = () => showPluckerModal();
  document.body.appendChild(btn);
  console.log("‼️ Comfy.OutputPlucker: Floating button added.");
}

function showPluckerModal() {
  if (document.getElementById("plucker-modal")) return;

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
  });

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
  });

  closeBtn.onclick = () => modal.remove();
  header.appendChild(title);
  header.appendChild(closeBtn);

  const iframe = document.createElement("iframe");
  iframe.src = "/plucker/view";
  Object.assign(iframe.style, {
    flex: "1",
    width: "100%",
    border: "none",
    backgroundColor: "#1e1e1e",
  });

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
