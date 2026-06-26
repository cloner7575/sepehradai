import { IconCheck } from './Icons';

const STEPS = ['واریز', 'آپلود رسید', 'تأیید'] as const;

export function PaymentStepper({ activeStep }: { activeStep: 0 | 1 | 2 }) {
  return (
    <div className="payment-stepper" aria-label="مراحل پرداخت">
      {STEPS.map((label, i) => {
        const done = i < activeStep;
        const active = i === activeStep;
        return (
          <div
            key={label}
            className={`payment-stepper-item${done ? ' is-done' : ''}${active ? ' is-active' : ''}`}
          >
            <span className="payment-stepper-dot">
              {done ? <IconCheck className="h-3 w-3" /> : i + 1}
            </span>
            <span className="payment-stepper-label">{label}</span>
          </div>
        );
      })}
    </div>
  );
}
