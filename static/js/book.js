/*
 * 3D kitob: sichqoncha ustiga kelganda kitob qaysi tomonda bo'lmasin,
 * old tomoniga silliq buriladi va muqovasi ochiladi. Ketganda aylanish davom etadi.
 */
(() => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  // CSS dagi bookspin animatsiyasining 0% holati bilan bir xil
  const FRONT = "rotateX(-10deg) rotateY(-28deg) rotateZ(0deg)";

  document.querySelectorAll("a.stage").forEach((stage) => {
    const book = stage.querySelector(".book3d");
    if (!book) return;

    const open = () => {
      if (stage.classList.contains("is-open")) return;
      const current = getComputedStyle(book).transform;
      book.style.animation = "none";
      book.style.transform = current;
      void book.offsetWidth; // brauzer joriy holatni qayd etsin
      book.style.transition = "transform 0.9s cubic-bezier(0.2, 0.8, 0.2, 1)";
      book.style.transform = FRONT;
      stage.classList.add("is-open");
    };

    const close = () => {
      if (!stage.classList.contains("is-open")) return;
      stage.classList.remove("is-open");
      book.style.transition = "";
      book.style.transform = "";
      book.style.animation = ""; // animatsiya 0% dan — aynan FRONT holatidan boshlanadi
    };

    stage.addEventListener("mouseenter", open);
    stage.addEventListener("mouseleave", close);
    stage.addEventListener("focus", open);
    stage.addEventListener("blur", close);
  });
})();
