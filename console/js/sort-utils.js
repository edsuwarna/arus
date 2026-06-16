/* SortUtils — reusable table sorting for Arus Console */
(function() {
  const _tables = {};

  window.SortUtils = {
    /**
     * Register a sortable table.
     * @param {string} id - unique table id (used as HTML id on <table>)
     * @param {string} dataKey - window property name holding the data array
     * @param {function[]} getters - per-column getter: (item) => sortable value
     * @param {string} renderFn - function name on window to re-render <tbody>
     */
    register(id, dataKey, getters, renderFn, defaultCol, defaultDir) {
      _tables[id] = { state: { col: defaultCol ?? null, dir: defaultDir || 'asc' }, dataKey, getters, renderFn };
      if (defaultCol != null) {
        // Sort data and show indicator immediately
        this.reapply(id);
      }
    },

    /**
     * Generate <th> HTML with sort indicator for use in template literals.
     */
    th(tableId, colIdx, label) {
      const t = _tables[tableId];
      if (!t) return `<th>${label}</th>`;
      const st = t.state;
      const active = st.col === colIdx;
      const icon = active ? (st.dir === 'asc' ? '▲' : '▼') : '↕';
      const opacity = active ? '' : 'opacity:0.45;';
      return `<th class="sortable" onclick="SortUtils.sort('${tableId}', ${colIdx})" style="cursor:pointer;user-select:none;">${label} <span class="sort-indicator" style="font-size:11px;font-weight:700;${opacity}">${icon}</span></th>`;
    },

    /**
     * Handle sort click — sorts data in-place and re-renders tbody.
     */
    sort(tableId, colIdx) {
      const t = _tables[tableId];
      if (!t) return;
      const st = t.state;

      if (st.col === colIdx) {
        st.dir = st.dir === 'asc' ? 'desc' : 'asc';
      } else {
        st.col = colIdx;
        st.dir = 'asc';
      }

      const data = window[t.dataKey];
      if (!data || data.length === 0) return;

      const getter = t.getters[colIdx];
      if (!getter) return;

      const dir = st.dir === 'asc' ? 1 : -1;
      data.sort((a, b) => {
        const va = getter(a);
        const vb = getter(b);
        if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir;
        return String(va).localeCompare(String(vb)) * dir;
      });

      if (t.renderFn && typeof window[t.renderFn] === 'function') {
        window[t.renderFn]();
      }
      this.updateIndicators(tableId);
    },

    updateIndicators(tableId) {
      const t = _tables[tableId];
      if (!t) return;
      const table = document.getElementById(tableId);
      if (!table) return;
      const ths = table.querySelectorAll('thead th.sortable');
      ths.forEach((th, idx) => {
        let indicator = th.querySelector('.sort-indicator');
        if (!indicator) {
          indicator = document.createElement('span');
          indicator.className = 'sort-indicator';
          indicator.style.cssText = 'font-size:11px;font-weight:700;';
          th.appendChild(indicator);
        }
        const isActive = t.state.col === idx;
        indicator.textContent = isActive ? (t.state.dir === 'asc' ? ' ▲' : ' ▼') : ' ↕';
        indicator.style.opacity = isActive ? '' : '0.45';
      });
    },

    /**
     * Apply current sort to data without toggling (e.g. on fresh data load).
     */
    reapply(tableId) {
      const t = _tables[tableId];
      if (!t || t.state.col === null) return;
      const colIdx = t.state.col;
      const data = window[t.dataKey];
      if (!data || data.length === 0) return;
      const getter = t.getters[colIdx];
      if (!getter) return;
      const dir = t.state.dir === 'asc' ? 1 : -1;
      data.sort((a, b) => {
        const va = getter(a);
        const vb = getter(b);
        if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir;
        return String(va).localeCompare(String(vb)) * dir;
      });
      this.updateIndicators(tableId);
    },
  };
})();
