import React from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Info,
  Leaf,
  ShieldCheck,
  SprayCan,
} from 'lucide-react';

type Content = string | string[] | null | undefined;

interface TreatmentGuidanceProps {
  language: 'en' | 'am';
  fieldPractices?: Content;
  prevention?: Content;
  pesticideOptions?: Content;
  safetyInstructions?: Content;
}

function toItems(content: Content): string[] {
  if (Array.isArray(content)) return content.filter((item) => Boolean(item));
  return typeof content === 'string' && content.trim() ? [content] : [];
}

function GuidanceList({ content }: { content: Content }) {
  const items = toItems(content);
  if (!items.length) return null;

  return (
    <ul className="space-y-2.5">
      {items.map((item, index) => (
        <li key={`${index}-${item}`} className="flex items-start gap-2.5 text-sm leading-relaxed text-stone-700 dark:text-stone-300">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700 dark:text-emerald-400" aria-hidden="true" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function SafetySteps({ content, language }: { content: Content; language: 'en' | 'am' }) {
  const items = toItems(content);
  if (!items.length) return null;

  const stepIcons = [ShieldCheck, SprayCan, Leaf, Info];
  const stepLabels = language === 'am'
    ? ['ከመጠቀም በፊት', 'በሚረጩበት ጊዜ', 'ከረጩ በኋላ', 'መመረዝ ወይም መጋለጥ ከተጠረጠረ']
    : ['Before use', 'During application', 'After application', 'If exposure is suspected'];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item, index) => {
        const Icon = stepIcons[index] || Info;
        const parts = item.match(/^([^:፦]{1,70})[:፦]\s*(.*)$/s);
        const body = parts?.[2] || item;
        return (
          <div key={`${index}-${item}`} className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4 dark:border-emerald-950 dark:bg-emerald-950/20">
            <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">
              <Icon className="h-5 w-5" aria-hidden="true" />
            </span>
            <h5 className="text-sm font-semibold text-stone-900 dark:text-stone-100">
              {parts?.[1] || stepLabels[index] || (language === 'am' ? 'የደህንነት ማስታወሻ' : 'Safety note')}
            </h5>
            <p className="mt-1.5 text-xs leading-relaxed text-stone-600 dark:text-stone-300">{body}</p>
          </div>
        );
      })}
    </div>
  );
}

function Disclosure({
  title,
  subtitle,
  icon: Icon,
  tone,
  children,
}: {
  title: string;
  subtitle: string;
  icon: typeof Leaf;
  tone: 'green' | 'blue' | 'rose';
  children: React.ReactNode;
}) {
  const toneClasses = {
    green: 'border-emerald-200 dark:border-emerald-900',
    blue: 'border-sky-200 dark:border-sky-900',
    rose: 'border-rose-200 dark:border-rose-900',
  };
  const iconClasses = {
    green: 'text-emerald-700 dark:text-emerald-400',
    blue: 'text-sky-700 dark:text-sky-400',
    rose: 'text-rose-700 dark:text-rose-400',
  };

  return (
    <details open className={`group rounded-xl border bg-white p-4 shadow-sm dark:bg-[#121A16] sm:p-5 ${toneClasses[tone]}`}>
      <summary className="flex cursor-pointer list-none items-center gap-3 [&::-webkit-details-marker]:hidden">
        <Icon className={`h-7 w-7 shrink-0 ${iconClasses[tone]}`} aria-hidden="true" />
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-bold text-stone-900 dark:text-stone-100">{title}</span>
          <span className="mt-0.5 block text-xs text-stone-500 dark:text-stone-400">{subtitle}</span>
        </span>
        <ChevronDown className="h-4 w-4 shrink-0 text-stone-500 transition-transform group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div className="mt-4 border-t border-stone-100 pt-4 dark:border-stone-800">{children}</div>
    </details>
  );
}

export const TreatmentGuidance: React.FC<TreatmentGuidanceProps> = ({
  language,
  fieldPractices,
  prevention,
  pesticideOptions,
  safetyInstructions,
}) => {
  const en = language !== 'am';
  const hasNonChemical = toItems(fieldPractices).length > 0 || toItems(prevention).length > 0;
  const hasPesticide = toItems(pesticideOptions).length > 0;
  const hasSafety = toItems(safetyInstructions).length > 0;

  if (!hasNonChemical && !hasPesticide && !hasSafety) return null;

  return (
    <section className="rounded-2xl border border-sky-100 bg-gradient-to-b from-sky-50/70 to-white p-4 dark:border-sky-950 dark:from-sky-950/20 dark:to-[#101713] sm:p-6">
      <div className="mb-5 flex items-start gap-3">
        <ShieldCheck className="mt-0.5 h-7 w-7 shrink-0 text-emerald-700 dark:text-emerald-400" aria-hidden="true" />
        <div>
          <h3 className="text-lg font-bold text-stone-900 dark:text-stone-100">
            {en ? 'Treatment & Pesticide Guidance' : 'የሕክምናና የጸረ-ተባይ መመሪያ'}
          </h3>
          <p className="mt-1 text-sm text-stone-600 dark:text-stone-300">
            {en ? 'Start with field practices. Use a pesticide only when needed and when locally approved.' : 'መጀመሪያ የእርሻ ልምዶችን ይከተሉ። የጸረ-ተባይ መድኃኒት ካስፈለገና በአካባቢው ከተፈቀደ ብቻ ይጠቀሙ።'}
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {hasNonChemical && (
          <Disclosure
            title={en ? 'Non-chemical control' : 'ከኬሚካል ውጭ የቁጥጥር ዘዴ'}
            subtitle={en ? 'Recommended first · field practices and prevention' : 'መጀመሪያ የሚመከር · የእርሻ ልምዶችና መከላከያ'}
            icon={Leaf}
            tone="green"
          >
            <div className="grid gap-5 md:grid-cols-2">
              {toItems(fieldPractices).length > 0 && (
                <div>
                  <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">{en ? 'Field practices' : 'የእርሻ ልምዶች'}</h4>
                  <GuidanceList content={fieldPractices} />
                </div>
              )}
              {toItems(prevention).length > 0 && (
                <div>
                  <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">{en ? 'Prevention' : 'መከላከያ'}</h4>
                  <GuidanceList content={prevention} />
                </div>
              )}
            </div>
            <div className="mt-4 flex items-start gap-2 rounded-lg bg-emerald-50 p-3 text-xs leading-relaxed text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
              <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{en ? 'These practices can reduce disease spread and may lower the need for chemical control.' : 'እነዚህ ልምዶች የበሽታ ስርጭትን ሊቀንሱና የኬሚካል መቆጣጠሪያ አስፈላጊነትን ሊያሳንሱ ይችላሉ።'}</span>
            </div>
          </Disclosure>
        )}

        {hasPesticide && (
          <Disclosure
            title={en ? 'Pesticide options' : 'የጸረ-ተባይ አማራጮች'}
            subtitle={en ? 'Only if needed · confirm locally approved products' : 'ካስፈለገ ብቻ · በአካባቢው የተፈቀደ ምርት መሆኑን ያረጋግጡ'}
            icon={SprayCan}
            tone="blue"
          >
            <GuidanceList content={pesticideOptions} />
            <div className="mt-4 flex items-start gap-2 rounded-lg bg-sky-50 p-3 text-xs leading-relaxed text-sky-900 dark:bg-sky-950/40 dark:text-sky-200">
              <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{en ? 'Product registration, crop approval and label directions can vary. Ask your local agricultural extension office to confirm the right product. Do not use a brand, dose or schedule unless it appears on that approved product label.' : 'የምርት ምዝገባ፣ ለሰብሉ የተሰጠ ፈቃድና የመለያ መመሪያ ሊለያዩ ይችላሉ። ትክክለኛውን ምርት ለማረጋገጥ የአካባቢውን የግብርና ባለሙያ ያማክሩ። በተፈቀደው የምርት መለያ ላይ ካልተጻፈ የንግድ ስም፣ መጠን ወይም የአጠቃቀም ጊዜ አይጠቀሙ።'}</span>
            </div>
          </Disclosure>
        )}

        {hasSafety && (
          <Disclosure
            title={en ? 'Safety instructions' : 'የደህንነት መመሪያዎች'}
            subtitle={en ? 'Protect yourself, other people, animals and the environment' : 'ራስዎን፣ ሌሎች ሰዎችን፣ እንስሳትንና አካባቢን ይጠብቁ'}
            icon={ShieldCheck}
            tone="rose"
          >
            <SafetySteps content={safetyInstructions} language={language} />
          </Disclosure>
        )}
      </div>

      <div className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-amber-950 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>{en ? 'General guidance only. Always read and follow the specific product label and consult a local agricultural expert before applying a pesticide.' : 'ይህ አጠቃላይ መመሪያ ብቻ ነው። የተወሰነውን የምርት መለያ ያንብቡና ይከተሉ፤ የጸረ-ተባይ መድኃኒት ከመጠቀምዎ በፊት የአካባቢውን የግብርና ባለሙያ ያማክሩ።'}</span>
      </div>
    </section>
  );
};
