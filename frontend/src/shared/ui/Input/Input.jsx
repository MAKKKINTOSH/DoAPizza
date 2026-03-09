import styles from './Input.module.css';

export function Input({
  value,
  onChange,
  type = 'text',
  placeholder = '',
  label,
  required = false,
  min,
  max,
  autoComplete,
  className = '',
  ...props
}) {
  const id = props.id || `input-${Math.random().toString(36).slice(2)}`;

  return (
    <div className={`${styles.wrapper} ${className}`}>
      {label && (
        <label htmlFor={id} className={styles.label}>
          {label}
          {required && <span className={styles.required}>*</span>}
        </label>
      )}
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        min={min}
        max={max}
        autoComplete={autoComplete}
        className={styles.input}
        {...props}
      />
    </div>
  );
}
