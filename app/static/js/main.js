/**
 * MetroCare General Hospital Client-side Script
 * Dynamic slot loading, date checks, and clean interactions.
 */

document.addEventListener('DOMContentLoaded', function () {
  // Auto-hide alert boxes
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = 'opacity 0.3s ease';
      alert.style.opacity = '0';
      setTimeout(function () {
        if (alert.parentNode) {
          alert.parentNode.removeChild(alert);
        }
      }, 300);
    }, 4500);
  });

  // Doctor consultation slot loading in booking form
  const doctorSelect = document.getElementById('doctor_select');
  const dateInput = document.getElementById('appointment_date');
  const slotContainer = document.getElementById('slots_container');
  const selectedTimeInput = document.getElementById('appointment_time');
  const feeDisplay = document.getElementById('consultation_fee_display');
  const slotStatusText = document.getElementById('slot_status_text');

  function fetchSlots() {
    if (!doctorSelect || !dateInput || !slotContainer) return;

    const doctorId = doctorSelect.value;
    const dateVal = dateInput.value;

    if (!doctorId || !dateVal) {
      slotContainer.innerHTML = '<div style="font-size:12px; color:var(--text-muted); grid-column:1/-1;">Please select a doctor and date to load available time slots.</div>';
      if (selectedTimeInput) selectedTimeInput.value = '';
      return;
    }

    slotContainer.innerHTML = '<div style="font-size:12px; color:var(--text-muted); grid-column:1/-1;">Loading available schedule...</div>';

    fetch(`/patient/api/doctor-slots/${doctorId}?date=${dateVal}`)
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          slotContainer.innerHTML = `<div style="font-size:12px; color:var(--status-cancelled); grid-column:1/-1;">${data.error}</div>`;
          return;
        }

        if (feeDisplay && data.consultation_fee) {
          feeDisplay.textContent = `₹${parseFloat(data.consultation_fee).toFixed(0)}`;
        }

        if (slotStatusText && data.available_days) {
          slotStatusText.textContent = `Doctor's working days: ${data.available_days}`;
        }

        slotContainer.innerHTML = '';

        if (!data.all_slots || data.all_slots.length === 0) {
          slotContainer.innerHTML = '<div style="font-size:12px; color:var(--text-muted); grid-column:1/-1;">No consultation slots configured for this doctor on this day.</div>';
          return;
        }

        data.all_slots.forEach(slot => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.textContent = slot;
          btn.className = 'slot-option';

          const isBooked = data.booked_slots.includes(slot);
          if (isBooked) {
            btn.classList.add('disabled');
            btn.disabled = true;
            btn.title = 'Slot Already Booked';
          } else {
            btn.addEventListener('click', function () {
              document.querySelectorAll('.slot-option').forEach(b => b.classList.remove('selected'));
              btn.classList.add('selected');
              if (selectedTimeInput) {
                selectedTimeInput.value = slot;
              }
            });
          }

          slotContainer.appendChild(btn);
        });
      })
      .catch(err => {
        console.error('Error fetching slots:', err);
        slotContainer.innerHTML = '<div style="font-size:12px; color:var(--status-cancelled); grid-column:1/-1;">Could not load slots. Please check network connection.</div>';
      });
  }

  if (doctorSelect) {
    doctorSelect.addEventListener('change', fetchSlots);
  }
  if (dateInput) {
    dateInput.addEventListener('change', fetchSlots);
    if (doctorSelect && doctorSelect.value && dateInput.value) {
      fetchSlots();
    }
  }
});
