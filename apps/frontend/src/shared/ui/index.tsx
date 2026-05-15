import React from 'react';

type ButtonVariant = 'default' | 'primary' | 'subtle';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'default', type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={['dictionary-button', variant === 'default' ? '' : variant, className].filter(Boolean).join(' ')}
      {...props}
    />
  ),
);
Button.displayName = 'Button';

export const IconButton = Button;

export interface CardProps extends React.HTMLAttributes<HTMLElement> {
  as?: 'div' | 'section' | 'article' | 'aside';
}

export const Card: React.FC<CardProps> = ({ as: Element = 'section', className = '', ...props }) =>
  React.createElement(Element, {
    className: ['dictionary-card', className].filter(Boolean).join(' '),
    ...props,
  });

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'accent';
}

export const Badge: React.FC<BadgeProps> = ({ className = '', variant = 'default', ...props }) => (
  <span
    className={['dictionary-badge', variant === 'accent' ? 'accent' : '', className].filter(Boolean).join(' ')}
    {...props}
  />
);

export const Tag = Badge;
export const ShelfChip = Badge;

export interface SearchBoxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string;
  shortcut?: string;
}

export const SearchBox = React.forwardRef<HTMLInputElement, SearchBoxProps>(
  ({ label, shortcut, className = '', ...props }, ref) => (
    <label className={['dictionary-searchbar', className].filter(Boolean).join(' ')}>
      <span aria-hidden="true">⌕</span>
      <span className="visually-hidden">{label}</span>
      <input ref={ref} type="search" aria-label={label} {...props} />
      {shortcut ? <kbd aria-hidden="true">{shortcut}</kbd> : null}
    </label>
  ),
);
SearchBox.displayName = 'SearchBox';

export interface SegmentedControlOption<T extends string> {
  value: T;
  label: string;
}

export interface SegmentedControlProps<T extends string> {
  label: string;
  value: T;
  options: SegmentedControlOption<T>[];
  onChange: (value: T) => void;
}

export function SegmentedControl<T extends string>({
  label,
  value,
  options,
  onChange,
}: SegmentedControlProps<T>) {
  return (
    <div className="dictionary-segmented" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export const EmptyState: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className = '', ...props }) => (
  <div className={['dictionary-empty', className].filter(Boolean).join(' ')} {...props} />
);

export const Skeleton: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className = '', ...props }) => (
  <div
    className={className}
    aria-hidden="true"
    style={{
      minHeight: '1rem',
      borderRadius: 6,
      background: 'linear-gradient(90deg, rgba(131,206,248,0.08), rgba(131,206,248,0.18), rgba(131,206,248,0.08))',
      ...props.style,
    }}
    {...props}
  />
);

export const InlineAction: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement>> = ({
  className = '',
  type = 'button',
  ...props
}) => (
  <button
    type={type}
    className={['dictionary-link-button', className].filter(Boolean).join(' ')}
    {...props}
  />
);

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ style, ...props }, ref) => (
    <input
      ref={ref}
      style={{
        width: '100%',
        border: '1px solid var(--dict-border)',
        borderRadius: 6,
        background: 'var(--dict-surface)',
        color: 'var(--dict-text)',
        padding: '0.55rem 0.7rem',
        ...style,
      }}
      {...props}
    />
  ),
);
Input.displayName = 'Input';

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ style, ...props }, ref) => (
    <textarea
      ref={ref}
      style={{
        width: '100%',
        border: '1px solid var(--dict-border)',
        borderRadius: 6,
        background: 'var(--dict-surface)',
        color: 'var(--dict-text)',
        padding: '0.55rem 0.7rem',
        ...style,
      }}
      {...props}
    />
  ),
);
Textarea.displayName = 'Textarea';

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ style, ...props }, ref) => (
    <select
      ref={ref}
      style={{
        border: '1px solid var(--dict-border)',
        borderRadius: 6,
        background: 'var(--dict-surface)',
        color: 'var(--dict-text)',
        padding: '0.45rem 0.7rem',
        ...style,
      }}
      {...props}
    />
  ),
);
Select.displayName = 'Select';

export const Switch = (props: React.InputHTMLAttributes<HTMLInputElement>) => (
  <input type="checkbox" role="switch" {...props} />
);

export const Drawer: React.FC<React.HTMLAttributes<HTMLDivElement>> = (props) => <div {...props} />;
export const SidePeek = Drawer;
export const Tabs = Drawer;
export const Tooltip = Drawer;
export const DataToolbar = Drawer;
export const MiniWordCard = Card;
export const CommandPalette = Drawer;
