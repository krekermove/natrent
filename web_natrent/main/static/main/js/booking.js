/* ==========================================================================
   NatRent — логика бронирования (выбор дат, гости, питомец)
   Чистый ванильный JavaScript, без зависимостей.
   Подключается в шаблоне через {% static 'rental/js/booking.js' %}
   ========================================================================== */
(function () {
  'use strict';

  var MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
  var MONTHS_SHORT = ['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'];
  var WEEKDAYS = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
  var GUEST_LIMIT = 10;

  function init() {
    var root = document.getElementById('booking');
    if (!root) return;

    // Лимит гостей берём из data-max-guests объекта (RentObject.max_guests),
    // если он задан; иначе — общий лимит по умолчанию.
    var maxGuestsAttr = parseInt(root.getAttribute('data-max-guests'), 10);
    var guestLimit = (maxGuestsAttr > 0) ? maxGuestsAttr : GUEST_LIMIT;

    var now = new Date();
    var state = {
      calOpen: false,
      guestsOpen: false,
      vy: now.getFullYear(),
      vm: now.getMonth(),
      start: null,
      end: null,
      adults: 1,
      children: 0,
      pet: false
    };

    // --- элементы ---
    var el = {
      datesTrigger: root.querySelector('[data-trigger="cal"]'),
      datesLabel:   root.querySelector('[data-label="dates"]'),
      guestsTrigger:root.querySelector('[data-trigger="guests"]'),
      guestsLabel:  root.querySelector('[data-label="guests"]'),
      calPop:       root.querySelector('[data-pop-el="cal"]'),
      guestPop:     root.querySelector('[data-pop-el="guests"]'),
      calBackdrop:  root.querySelector('[data-backdrop="cal"]'),
      guestBackdrop:root.querySelector('[data-backdrop="guests"]'),
      calDesktop:   root.querySelector('[data-cal-desktop]'),
      calMobile:    root.querySelector('[data-cal-mobile]'),
      calMobileScroll: root.querySelector('[data-cal-scroll]'),
      leftTitle:    root.querySelector('[data-cal="leftTitle"]'),
      rightTitle:   root.querySelector('[data-cal="rightTitle"]'),
      leftGrid:     root.querySelector('[data-cal="leftGrid"]'),
      rightGrid:    root.querySelector('[data-cal="rightGrid"]'),
      prevBtn:      root.querySelector('[data-cal="prev"]'),
      nextBtn:      root.querySelector('[data-cal="next"]'),
      form:         root.querySelector('form')
    };

    function midnight() { var d = new Date(); d.setHours(0,0,0,0); return d.getTime(); }
    function fmtShort(ms) { var d = new Date(ms); return d.getDate() + ' ' + MONTHS_SHORT[d.getMonth()]; }
    function pad2(n) { return n < 10 ? '0' + n : String(n); }
    function fmtInputDate(ms) { var d = new Date(ms); return pad2(d.getDate()) + '.' + pad2(d.getMonth() + 1) + '.' + d.getFullYear(); }
    function isMobile() { return window.matchMedia('(max-width:760px)').matches; }

    function plural(c) {
      if (c === 1) return '1 гость';
      var m10 = c % 10, m100 = c % 100;
      if (m10 >= 2 && m10 <= 4 && !(m100 >= 12 && m100 <= 14)) return c + ' гостя';
      return c + ' гостей';
    }

    // --- выбор диапазона дат ---
    function pickDate(ms) {
      if (state.start == null || state.end != null) { state.start = ms; state.end = null; }
      else if (ms === state.start) { /* без изменений */ }
      else if (ms < state.start) { state.start = ms; state.end = null; }
      else { state.end = ms; }
      renderCalendar();
      renderLabels();
    }

    // --- построение сетки месяца ---
    function buildGrid(year, month) {
      var first = new Date(year, month, 1);
      var lead = (first.getDay() + 6) % 7;
      var total = new Date(year, month + 1, 0).getDate();
      var today = midnight();
      var frag = document.createDocumentFragment();
      var i, d;

      for (i = 0; i < lead; i++) {
        var e = document.createElement('div');
        e.className = 'day is-empty';
        frag.appendChild(e);
      }
      for (d = 1; d <= total; d++) {
        var ms = new Date(year, month, d).getTime();
        var past = ms < today;
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'day';
        btn.textContent = String(d);
        if (past) {
          btn.className += ' is-past';
          btn.disabled = true;
        } else {
          var isStart = state.start != null && ms === state.start;
          var isEnd   = state.end != null && ms === state.end;
          var inRange = state.start != null && state.end != null && ms > state.start && ms < state.end;
          if (isStart || isEnd) btn.className += ' is-edge';
          else if (inRange) btn.className += ' is-inrange';
          else if (ms === today) btn.className += ' is-today';
          btn.setAttribute('data-ms', String(ms));
        }
        frag.appendChild(btn);
      }
      return frag;
    }

    // --- рендер десктопного календаря (2 месяца) ---
    function renderCalendar() {
      // десктоп
      var ly = state.vy, lm = state.vm;
      var rm = lm + 1, ry = ly; if (rm > 11) { rm = 0; ry++; }
      el.leftTitle.textContent = MONTHS[lm] + ' ' + ly;
      el.rightTitle.textContent = MONTHS[rm] + ' ' + ry;
      el.leftGrid.innerHTML = '';  el.leftGrid.appendChild(buildGrid(ly, lm));
      el.rightGrid.innerHTML = ''; el.rightGrid.appendChild(buildGrid(ry, rm));
      var atCurrent = (state.vy === now.getFullYear() && state.vm === now.getMonth());
      el.prevBtn.classList.toggle('is-hidden', atCurrent);

      // мобайл — рендерим лениво (12 месяцев вперёд от текущего)
      if (el.calMobile && !el.calMobile.getAttribute('data-built')) {
        var my = now.getFullYear(), mmo = now.getMonth();
        for (var k = 0; k < 12; k++) {
          var wrap = document.createElement('div');
          wrap.className = 'cal-scroll__month';
          var title = document.createElement('div');
          title.className = 'cal-scroll__title';
          title.textContent = MONTHS[mmo] + ' ' + my;
          var grid = document.createElement('div');
          grid.className = 'cal-grid';
          grid.setAttribute('data-mobile-grid', my + '-' + mmo);
          wrap.appendChild(title); wrap.appendChild(grid);
          el.calMobileScroll.appendChild(wrap);
          mmo++; if (mmo > 11) { mmo = 0; my++; }
        }
        el.calMobile.setAttribute('data-built', '1');
      }
      // обновляем мобильные сетки
      if (el.calMobileScroll) {
        var grids = el.calMobileScroll.querySelectorAll('[data-mobile-grid]');
        grids.forEach(function (g) {
          var parts = g.getAttribute('data-mobile-grid').split('-');
          g.innerHTML = '';
          g.appendChild(buildGrid(parseInt(parts[0], 10), parseInt(parts[1], 10)));
        });
      }
    }

    function renderLabels() {
      var dl = 'Выберите даты';
      if (state.start != null && state.end != null) dl = fmtShort(state.start) + ' — ' + fmtShort(state.end);
      else if (state.start != null) dl = fmtShort(state.start) + ' — …';
      el.datesLabel.textContent = dl;

      if (el.form) {
        var inp1 = el.form.querySelector('[name="firstInputDate"]');
        var inp2 = el.form.querySelector('[name="secondInputDate"]');
        if (inp1) inp1.value = state.start != null ? fmtInputDate(state.start) : '';
        if (inp2) inp2.value = state.end != null ? fmtInputDate(state.end) : '';
      }

      var total = state.adults + state.children;
      var gl = plural(total);
      if (state.pet) gl += ' · питомец';
      el.guestsLabel.textContent = gl;

      if (el.form) {
        var gIn = el.form.querySelector('[name="guest_count"]');
        var cIn = el.form.querySelector('[name="children_under_3"]');
        var pIn = el.form.querySelector('[name="has_pet"]');
        if (gIn) gIn.value = total;
        if (cIn) cIn.value = state.children;
        if (pIn) pIn.value = state.pet ? 'true' : 'false';
      }
    }

    // --- гости ---
    function renderGuests() {
      var total = state.adults + state.children;
      root.querySelector('[data-val="adults"]').textContent = state.adults;
      root.querySelector('[data-val="children"]').textContent = state.children;
      root.querySelector('[data-step="adults-dec"]').disabled = state.adults <= 1;
      root.querySelector('[data-step="adults-inc"]').disabled = total >= guestLimit;
      root.querySelector('[data-step="children-dec"]').disabled = state.children <= 0;
      root.querySelector('[data-step="children-inc"]').disabled = total >= guestLimit;
      var petSwitch = root.querySelector('[data-switch="pet"]');
      if (petSwitch) petSwitch.classList.toggle('on', state.pet);
      renderLabels();
    }

    // --- открытие/закрытие ---
    function lockBody() {
      document.body.style.overflow = (isMobile() && (state.calOpen || state.guestsOpen)) ? 'hidden' : '';
    }
    function setCal(open) {
      state.calOpen = open; if (open) setGuests(false);
      el.calPop.classList.toggle('open', open);
      if (el.calBackdrop) el.calBackdrop.classList.toggle('open', open && isMobile());
      lockBody();
    }
    function setGuests(open) {
      state.guestsOpen = open; if (open) { state.calOpen = false; el.calPop.classList.remove('open'); if (el.calBackdrop) el.calBackdrop.classList.remove('open'); }
      el.guestPop.classList.toggle('open', open);
      if (el.guestBackdrop) el.guestBackdrop.classList.toggle('open', open && isMobile());
      lockBody();
    }

    // ==== события ====
    // определяем скролл vs тап — не открываем попапы если палец двигался
    var touchScrolling = false;
    document.addEventListener('touchstart', function () { touchScrolling = false; }, { passive: true });
    document.addEventListener('touchmove',  function () { touchScrolling = true;  }, { passive: true });

    el.datesTrigger.addEventListener('click', function (e) { if (touchScrolling) return; e.stopPropagation(); setCal(!state.calOpen); });
    el.guestsTrigger.addEventListener('click', function (e) { if (touchScrolling) return; e.stopPropagation(); setGuests(!state.guestsOpen); });

    el.prevBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var m = state.vm - 1, y = state.vy; if (m < 0) { m = 11; y--; }
      state.vm = m; state.vy = y; renderCalendar();
    });
    el.nextBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var m = state.vm + 1, y = state.vy; if (m > 11) { m = 0; y++; }
      state.vm = m; state.vy = y; renderCalendar();
    });

    // делегирование клика по дням (десктоп + мобайл)
    el.calPop.addEventListener('click', function (e) {
      var b = e.target.closest('[data-ms]');
      if (b) { e.stopPropagation(); pickDate(parseInt(b.getAttribute('data-ms'), 10)); }
    });

    // сброс / закрытие / применить
    root.querySelectorAll('[data-action="clear-dates"]').forEach(function (b) {
      b.addEventListener('click', function (e) { e.stopPropagation(); state.start = null; state.end = null; renderCalendar(); renderLabels(); });
    });
    root.querySelectorAll('[data-action="close-cal"]').forEach(function (b) {
      b.addEventListener('click', function (e) { e.stopPropagation(); setCal(false); });
    });
    root.querySelectorAll('[data-action="close-guests"]').forEach(function (b) {
      b.addEventListener('click', function (e) { e.stopPropagation(); setGuests(false); });
    });
    if (el.calBackdrop) el.calBackdrop.addEventListener('click', function () { setCal(false); });
    if (el.guestBackdrop) el.guestBackdrop.addEventListener('click', function () { setGuests(false); });

    // степперы гостей
    function bindStep(sel, fn) {
      var b = root.querySelector(sel);
      if (b) b.addEventListener('click', function (e) { e.stopPropagation(); fn(); renderGuests(); });
    }
    bindStep('[data-step="adults-inc"]',   function () { if (state.adults + state.children < guestLimit) state.adults++; });
    bindStep('[data-step="adults-dec"]',   function () { if (state.adults > 1) state.adults--; });
    bindStep('[data-step="children-inc"]', function () { if (state.adults + state.children < guestLimit) state.children++; });
    bindStep('[data-step="children-dec"]', function () { if (state.children > 0) state.children--; });
    var petSwitchBtn = root.querySelector('[data-switch="pet"]');
    if (petSwitchBtn) petSwitchBtn.addEventListener('click', function (e) { e.stopPropagation(); state.pet = !state.pet; renderGuests(); });

    // клик вне поповеров (десктоп)
    document.addEventListener('mousedown', function (e) {
      if (state.calOpen && !e.target.closest('[data-pop="cal"]') && !e.target.closest('[data-pop-el="cal"]')) setCal(false);
      if (state.guestsOpen && !e.target.closest('[data-pop="guests"]') && !e.target.closest('[data-pop-el="guests"]')) setGuests(false);
    });

    // ресайз — снять блокировку при переходе на десктоп
    window.addEventListener('resize', lockBody);

    // закрытие попапов по сигналу от sticky-скрипта
    document.addEventListener('booking:closePopups', function () {
      if (state.calOpen) setCal(false);
      if (state.guestsOpen) setGuests(false);
    });

    // сохраняем состояние перед отправкой формы
    if (el.form) {
      el.form.addEventListener('submit', function () {
        sessionStorage.setItem('bk_restore', JSON.stringify({
          start: state.start, end: state.end,
          adults: state.adults, children: state.children, pet: state.pet
        }));
      });
    }

    // восстанавливаем состояние после перезагрузки (после POST)
    var _saved = sessionStorage.getItem('bk_restore');
    if (_saved) {
      try {
        var _s = JSON.parse(_saved);
        sessionStorage.removeItem('bk_restore');
        if (_s.start   != null) state.start    = _s.start;
        if (_s.end     != null) state.end      = _s.end;
        if (_s.adults   > 0)   state.adults   = _s.adults;
        if (_s.children >= 0)  state.children = _s.children;
        if (_s.pet     != null) state.pet      = !!_s.pet;
      } catch (e) { /* ignore */ }
    }

    // первый рендер
    renderCalendar();
    renderGuests();
    renderLabels();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
