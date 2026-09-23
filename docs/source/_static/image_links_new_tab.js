// open image links, i.e. images with a `:target:`, in a new tab
document.addEventListener("DOMContentLoaded", () => {
    for (const link of document.querySelectorAll("a.image-reference")) {
        link.target = "_blank";
        link.rel = "noopener";
    }
});
