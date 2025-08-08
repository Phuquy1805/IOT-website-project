import React from 'react';
import '../styles/toggle.css';

export default function BigToggle({ id = 'bigToggle', checked, disabled, onChange, label }) {
  return (
    <div
      className={[
        'big-toggle',
        checked ? 'big-toggle--open' : 'big-toggle--closed',
        disabled ? 'big-toggle--disabled' : '',
      ].join(' ')}
    >
      <input
        id={id}
        type="checkbox"
        className="big-toggle__input"
        checked={checked}
        disabled={disabled}
        onChange={onChange}
      />

      <label htmlFor={id} className="big-toggle__track">
        <span className="big-toggle__knob" />
      </label>

      {label ? <div className="big-toggle__state">{label}</div> : null}
    </div>
  );
}
