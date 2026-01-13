function filterReports() {
    const search = document.getElementById("searchInput").value.toLowerCase();
    const type = document.getElementById("typeFilter").value;

    const cards = document.querySelectorAll(".report-card");

    cards.forEach(card => {
        const text = card.dataset.text.toLowerCase();
        const cardType = card.dataset.type;

        const matchesSearch = text.includes(search);
        const matchesType = !type || cardType === type;

        card.style.display = (matchesSearch && matchesType)
            ? "block"
            : "none";
    });
}
