(function () {
  const toast = document.querySelector("[data-toast]");

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.hidden = false;
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
      toast.hidden = true;
    }, 2600);
  }

  function money(value) {
    return `Rs. ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(Number(value || 0))}`;
  }

  function number(value) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(Number(value || 0));
  }

  function categoryActivity(products) {
    return products.reduce((totals, product) => {
      const category = product.category || "Other";
      const stats = totals.get(category) || {
        productCount: 0,
        views: 0,
        carts: 0,
        sold: 0,
        stock: 0,
      };
      stats.productCount += 1;
      stats.views += Number(product.views_count || 0);
      stats.carts += Number(product.carts_count || 0);
      stats.sold += Number(product.sold_count || 0);
      stats.stock += Math.max(0, Number(product.stock || 0));
      totals.set(category, stats);
      return totals;
    }, new Map());
  }

  async function refreshCategories() {
    const tiles = document.querySelectorAll("[data-category-tile]");
    if (!tiles.length) return;
    try {
      const products = await fetch("/api/products").then((response) => response.json());
      const statsByCategory = categoryActivity(products);
      tiles.forEach((tile) => {
        const category = tile.dataset.category;
        const stats = statsByCategory.get(category);
        if (!stats) return;
        const activity = stats.views + stats.carts * 2 + stats.sold * 3;
        const countNode = tile.querySelector("[data-category-count]");
        const productNode = tile.querySelector("[data-category-products]");
        const secondaryNode = tile.querySelector("[data-category-secondary]");
        if (countNode) countNode.textContent = number(activity);
        if (secondaryNode) secondaryNode.textContent = number(stats.stock);
        if (productNode) productNode.lastChild.textContent = " units live";
      });
    } catch (error) {
      showToast("Live category activity is reconnecting.");
    }
  }

  async function refreshDashboard() {
    const metricRoot = document.querySelector("[data-metric]");
    if (!metricRoot) return;
    try {
      const metrics = await fetch("/api/metrics").then((response) => response.json());
      Object.entries(metrics).forEach(([key, value]) => {
        const node = document.querySelector(`[data-metric="${key}"]`);
        if (!node) return;
        node.textContent = key === "total_revenue" || key === "pos_revenue" ? money(value) : number(value);
      });
    } catch (error) {
      // Keep the dashboard calm if the user is logged out in another tab.
      showToast("Live marketplace metrics are reconnecting.");
    }
  }

  window.setInterval(refreshDashboard, 8000);
  window.setInterval(refreshCategories, 8000);
})();
