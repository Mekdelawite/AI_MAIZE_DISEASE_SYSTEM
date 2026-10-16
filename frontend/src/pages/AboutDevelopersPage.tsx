import React from 'react';
import {
  ArrowDownRight,
  Brain,
  Code2,
  Database,
  Globe,
  Layers,
  Leaf,
  Network,
  ShieldCheck,
  Sprout,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import heroMaizeImage from '../assets/images/hero_ethiopian_maize_farm_1791572380074.jpg';
import leafInspectionImage from '../assets/images/maize_leaf_inspection_1791572392418.jpg';
import { PublicLayout } from '../components/layout/PublicLayout';
import { useApp } from '../context/AppContext';

const developers = [
  {
    name: 'Nigusu Tigabu', initials: 'NT', role: 'aboutRoleBackend', summary: 'aboutNigusuSummary',
    responsibilities: ['aboutNigusuResponsibility1', 'aboutNigusuResponsibility2', 'aboutNigusuResponsibility3', 'aboutNigusuResponsibility4'],
    skills: ['Flask', 'PostgreSQL', 'REST API', 'JWT'], icon: Database, accent: 'from-emerald-900 to-emerald-700',
  },
  {
    name: 'Rediet Tsega', initials: 'RT', role: 'aboutRoleAI', summary: 'aboutRedietSummary',
    responsibilities: ['aboutRedietResponsibility1', 'aboutRedietResponsibility2', 'aboutRedietResponsibility3', 'aboutRedietResponsibility4'],
    skills: ['TensorFlow/Keras', 'MobileNetV2', 'Grad-CAM', 'Python'], icon: Brain, accent: 'from-amber-800 to-yellow-600',
  },
  {
    name: 'Samuael Admasu', initials: 'SA', role: 'aboutRoleFrontend', summary: 'aboutSamuaelSummary',
    responsibilities: ['aboutSamuaelResponsibility1', 'aboutSamuaelResponsibility2', 'aboutSamuaelResponsibility3', 'aboutSamuaelResponsibility4'],
    skills: ['React', 'TypeScript', 'Responsive UI', 'API integration'], icon: Code2, accent: 'from-teal-900 to-emerald-600',
  },
];

const timeline = [
  ['aboutStage1Title', 'aboutStage1Text', Leaf],
  ['aboutStage2Title', 'aboutStage2Text', Database],
  ['aboutStage3Title', 'aboutStage3Text', Brain],
  ['aboutStage4Title', 'aboutStage4Text', Network],
  ['aboutStage5Title', 'aboutStage5Text', Code2],
  ['aboutStage6Title', 'aboutStage6Text', Layers],
] as const;

const technologies = [
  ['React', 'aboutTechReact', Code2], ['Python', 'aboutTechPython', Brain],
  ['Flask', 'aboutTechFlask', Network], ['PostgreSQL', 'aboutTechPostgres', Database],
  ['TensorFlow/Keras', 'aboutTechTensorflow', Layers], ['MobileNetV2', 'aboutTechMobileNet', Leaf],
  ['Grad-CAM', 'aboutTechGradcam', Globe], ['JWT', 'aboutTechJwt', ShieldCheck],
] as const;

const capabilities = [
  'aboutDiseaseNlb', 'aboutDiseaseRust', 'aboutDiseaseGray', 'aboutDiseaseHealthy',
];

export const AboutDevelopersPage: React.FC = () => {
  const { t } = useApp();

  return (
    <PublicLayout>
      <div className="overflow-hidden bg-[#faf8f3] text-stone-900 dark:bg-[#0c1310] dark:text-stone-100">
        <section className="relative isolate border-b border-stone-200/80 bg-[#f4f1e8] dark:border-stone-800 dark:bg-[#101a14]">
          <div className="absolute inset-0 -z-10 opacity-40 [background-image:radial-gradient(#57734d_0.65px,transparent_0.65px)] [background-size:18px_18px] dark:opacity-15" aria-hidden="true" />
          <div className="mx-auto grid min-h-[640px] max-w-[1440px] items-center gap-12 px-6 py-14 sm:px-10 sm:py-20 lg:grid-cols-[0.92fr_1.08fr] lg:gap-16 lg:px-16 lg:py-20">
            <div className="about-reveal relative z-10 max-w-2xl">
              <p className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-emerald-900 dark:text-emerald-300">
                <span className="h-px w-8 bg-amber-600" />{t('aboutHeroEyebrow')}
              </p>
              <h1 className="mt-6 max-w-2xl font-display text-[clamp(2.65rem,6vw,5.3rem)] font-semibold leading-[1.04] tracking-[-0.055em] text-emerald-950 dark:text-stone-50">
                {t('aboutHeroTitle')}
              </h1>
              <p className="mt-6 max-w-xl text-base leading-8 text-stone-700 dark:text-stone-300 sm:text-lg">
                {t('aboutHeroText')}
              </p>
              <div className="mt-9 flex flex-wrap gap-3">
                <a href="#project-history" className="inline-flex min-h-12 items-center gap-3 bg-emerald-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-amber-600 dark:bg-emerald-700 dark:hover:bg-emerald-600">
                  {t('aboutExploreProject')}<ArrowDownRight className="h-4 w-4" aria-hidden="true" />
                </a>
                <a href="#developers" className="inline-flex min-h-12 items-center border border-stone-300 bg-white/70 px-5 py-3 text-sm font-semibold text-stone-800 transition hover:border-emerald-800 hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-amber-600 dark:border-stone-700 dark:bg-stone-900/50 dark:text-stone-100 dark:hover:border-emerald-400">
                  {t('aboutMeetDevelopers')}
                </a>
              </div>
              <p className="mt-9 text-xs font-medium uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">{t('aboutProjectName')}</p>
            </div>

            <div className="about-reveal relative mx-auto w-full max-w-2xl lg:justify-self-end" style={{ animationDelay: '120ms' }}>
              <div className="absolute -bottom-4 -left-4 h-2/3 w-2/3 border-b border-l border-amber-600/70 dark:border-amber-400/60" aria-hidden="true" />
              <div className="relative h-[360px] overflow-hidden bg-emerald-950 shadow-[0_30px_80px_-36px_rgba(12,42,26,0.55)] sm:h-[440px] lg:h-[520px]">
                <img src={heroMaizeImage} alt={t('aboutHeroImageAlt')} className="h-full w-full object-cover transition-transform duration-700 hover:scale-[1.025] motion-reduce:transition-none" />
                <div className="absolute inset-0 bg-gradient-to-t from-[#071a10]/85 via-[#071a10]/10 to-transparent" aria-hidden="true" />
                <div className="absolute inset-0 border-[12px] border-white/10" aria-hidden="true" />
                <div className="absolute left-6 top-6 flex items-center gap-2 border border-white/25 bg-emerald-950/55 px-3 py-2 text-xs font-semibold tracking-wide text-white backdrop-blur-sm sm:left-8 sm:top-8">
                  <span className="h-2 w-2 rounded-full bg-amber-300" />{t('aboutProjectName')}
                </div>
                <div className="absolute bottom-7 left-7 right-7 flex items-end justify-between gap-4 text-white sm:bottom-10 sm:left-10 sm:right-10">
                  <p className="max-w-md font-display text-2xl font-semibold leading-tight tracking-tight sm:text-3xl">{t('aboutProjectCardTitle')}</p>
                  <Sprout className="mb-1 hidden h-9 w-9 shrink-0 text-amber-200 sm:block" aria-hidden="true" />
                </div>
                <div className="absolute right-6 top-24 hidden h-28 w-28 rounded-full border border-white/30 sm:block" aria-hidden="true">
                  <span className="absolute inset-3 rounded-full border border-dashed border-amber-200/70" />
                  <span className="absolute inset-[31px] rounded-full bg-amber-200/20" />
                  <span className="absolute -right-1 top-1/2 h-2 w-2 rounded-full bg-amber-200" />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="developers" className="scroll-mt-24 px-6 py-20 sm:px-10 sm:py-24 lg:px-16">
          <div className="mx-auto max-w-[1320px]">
            <div className="mb-12 grid gap-5 md:grid-cols-[0.8fr_1.2fr] md:items-end">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-800 dark:text-emerald-300">{t('aboutTeamEyebrow')}</p>
                <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-emerald-950 dark:text-white sm:text-4xl">{t('aboutTeamTitle')}</h2>
              </div>
              <p className="max-w-2xl text-sm leading-7 text-stone-600 dark:text-stone-300 md:justify-self-end">{t('aboutTeamIntro')}</p>
            </div>
            <div className="grid items-stretch gap-5 lg:grid-cols-3">
              {developers.map((developer, index) => {
                const Icon = developer.icon;
                return (
                  <article key={developer.name} className="about-reveal group flex h-full flex-col border border-stone-200 bg-white transition duration-300 hover:-translate-y-1 hover:border-emerald-900/30 hover:shadow-[0_24px_50px_-32px_rgba(10,50,30,0.45)] dark:border-stone-800 dark:bg-[#121a16] dark:hover:border-emerald-300/30" style={{ animationDelay: `${index * 90}ms` }}>
                    <div className={`relative flex h-48 items-end overflow-hidden bg-gradient-to-br ${developer.accent} p-6 text-white sm:h-56`}>
                      <div className="absolute -right-8 -top-12 h-48 w-48 rounded-full border border-white/15" aria-hidden="true" />
                      <div className="absolute -right-1 top-4 h-32 w-32 rounded-full border border-dashed border-white/20" aria-hidden="true" />
                      <span className="relative font-display text-7xl font-semibold tracking-[-0.08em] text-white/90 sm:text-8xl">{developer.initials}</span>
                      <span className="absolute bottom-6 right-6 flex h-11 w-11 items-center justify-center border border-white/25 bg-white/10 backdrop-blur-sm">
                        <Icon className="h-5 w-5" aria-hidden="true" />
                      </span>
                      <span className="absolute left-6 top-6 border border-white/30 bg-black/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.15em] text-white backdrop-blur-sm">{t('aboutAvatarPlaceholder')}</span>
                    </div>
                    <div className="flex flex-1 flex-col p-6 sm:p-7">
                      <span className="w-fit bg-emerald-50 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-emerald-900 dark:bg-emerald-950/70 dark:text-emerald-200">{t(developer.role)}</span>
                      <h3 className="mt-4 font-display text-xl font-semibold tracking-tight text-stone-950 dark:text-white">{developer.name}</h3>
                      <p className="mt-3 text-sm leading-6 text-stone-600 dark:text-stone-300">{t(developer.summary)}</p>
                      <ul className="mt-5 space-y-2.5 border-t border-stone-100 pt-5 text-sm leading-6 text-stone-700 dark:border-stone-800 dark:text-stone-300">
                        {developer.responsibilities.map((key) => <li key={key} className="flex gap-2.5"><span className="mt-[9px] h-1.5 w-1.5 shrink-0 bg-amber-600 dark:bg-amber-400" />{t(key)}</li>)}
                      </ul>
                      <div className="mt-auto flex flex-wrap gap-2 pt-6">
                        {developer.skills.map((skill) => <span key={skill} className="border border-stone-200 px-2.5 py-1 text-[10px] font-medium tracking-wide text-stone-600 dark:border-stone-700 dark:text-stone-300">{skill}</span>)}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section id="project-overview" className="scroll-mt-24 border-y border-stone-200 bg-[#f0eee5] px-6 py-20 dark:border-stone-800 dark:bg-[#101814] sm:px-10 sm:py-24 lg:px-16">
          <div className="mx-auto grid max-w-[1320px] items-center gap-10 lg:grid-cols-[1fr_1fr] lg:gap-16">
            <div className="about-reveal relative min-h-[320px] overflow-hidden sm:min-h-[430px]">
              <img src={leafInspectionImage} alt={t('aboutLeafImageAlt')} className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 hover:scale-[1.025] motion-reduce:transition-none" />
              <div className="absolute inset-0 bg-gradient-to-t from-emerald-950/75 via-transparent to-transparent" aria-hidden="true" />
              <p className="absolute bottom-6 left-6 right-6 font-display text-xl font-semibold text-white sm:bottom-8 sm:left-8 sm:text-2xl">{t('aboutOverviewEyebrow')}</p>
            </div>
            <div className="about-reveal" style={{ animationDelay: '100ms' }}>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-800 dark:text-emerald-300">{t('aboutOverviewEyebrow')}</p>
              <h2 className="mt-4 max-w-xl font-display text-3xl font-semibold leading-tight tracking-tight text-emerald-950 dark:text-white sm:text-4xl">{t('aboutOverviewTitle')}</h2>
              <p className="mt-5 max-w-2xl text-sm leading-7 text-stone-700 dark:text-stone-300 sm:text-base">{t('aboutOverviewText')}</p>
              <div className="mt-7 grid grid-cols-2 gap-2.5">
                {capabilities.map((key, index) => <div key={key} className="flex min-h-16 items-center gap-3 border border-stone-300/80 bg-white/70 px-3 py-3 dark:border-stone-700 dark:bg-stone-900/50"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-900/10 text-[10px] font-bold text-emerald-900 dark:bg-emerald-100/10 dark:text-emerald-200">0{index + 1}</span><p className="text-xs font-semibold leading-5 text-stone-800 dark:text-stone-100 sm:text-sm">{t(key)}</p></div>)}
              </div>
              <div className="mt-6 flex items-start gap-3 border-l-2 border-amber-600 bg-amber-50/70 p-4 text-xs leading-6 text-stone-700 dark:border-amber-400 dark:bg-amber-950/20 dark:text-stone-300">
                <ShieldCheck className="mt-1 h-4 w-4 shrink-0 text-emerald-800 dark:text-emerald-300" aria-hidden="true" />{t('aboutAvailabilityNote')}
              </div>
            </div>
          </div>
        </section>

        <section id="project-history" className="scroll-mt-24 px-6 py-20 sm:px-10 sm:py-24 lg:px-16">
          <div className="mx-auto max-w-[1120px]">
            <div className="mb-12 max-w-2xl">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-800 dark:text-emerald-300">{t('aboutHistoryEyebrow')}</p>
              <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-emerald-950 dark:text-white sm:text-4xl">{t('aboutHistoryTitle')}</h2>
              <p className="mt-4 text-sm leading-7 text-stone-600 dark:text-stone-300">{t('aboutHistoryIntro')}</p>
            </div>
            <ol className="relative space-y-5 before:absolute before:bottom-8 before:left-[21px] before:top-8 before:w-px before:bg-emerald-900/20 dark:before:bg-emerald-100/20">
              {timeline.map(([titleKey, textKey, Icon], index) => (
                <li key={titleKey} className="about-reveal relative grid grid-cols-[44px_1fr] gap-4 sm:grid-cols-[64px_1fr] sm:gap-6" style={{ animationDelay: `${index * 65}ms` }}>
                  <div className="relative z-10 flex h-11 w-11 items-center justify-center border border-emerald-900/20 bg-[#f4f1e8] text-emerald-900 dark:border-emerald-100/15 dark:bg-[#17231c] dark:text-emerald-200 sm:h-12 sm:w-12">
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-amber-500 text-[9px] font-bold text-emerald-950">{index + 1}</span>
                  </div>
                  <div className="mb-2 border border-stone-200 bg-white p-5 dark:border-stone-800 dark:bg-[#121a16] sm:p-6">
                    <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-emerald-800 dark:text-emerald-300">{t('aboutStageLabel')} {index + 1}</p>
                    <h3 className="mt-2 font-display text-base font-semibold text-stone-950 dark:text-white sm:text-lg">{t(titleKey)}</h3>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-600 dark:text-stone-300">{t(textKey)}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="technologies" className="scroll-mt-24 border-y border-stone-200 bg-[#f4f1e8] px-6 py-20 dark:border-stone-800 dark:bg-[#101814] sm:px-10 sm:py-24 lg:px-16">
          <div className="mx-auto max-w-[1320px]">
            <div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div><p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-800 dark:text-emerald-300">{t('aboutTechEyebrow')}</p><h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-emerald-950 dark:text-white sm:text-4xl">{t('aboutTechTitle')}</h2></div>
              <p className="max-w-lg text-sm leading-6 text-stone-600 dark:text-stone-300">{t('aboutTechIntro')}</p>
            </div>
            <div className="grid grid-cols-2 gap-px border border-stone-300 bg-stone-300 dark:border-stone-700 dark:bg-stone-700 sm:grid-cols-4">
              {technologies.map(([name, descriptionKey, Icon]) => <div key={name} className="min-h-32 bg-[#faf8f3] p-4 transition-colors hover:bg-white dark:bg-[#121a16] dark:hover:bg-[#17231c] sm:p-5"><div className="flex items-center gap-3"><Icon className="h-4 w-4 shrink-0 text-emerald-800 dark:text-emerald-300" aria-hidden="true" /><h3 className="text-sm font-semibold text-stone-950 dark:text-white">{name}</h3></div><p className="mt-3 text-xs leading-5 text-stone-600 dark:text-stone-400">{t(descriptionKey)}</p></div>)}
            </div>
          </div>
        </section>

        <section className="px-6 py-16 sm:px-10 sm:py-20 lg:px-16">
          <div className="relative mx-auto max-w-[1320px] overflow-hidden bg-[#103b27] px-6 py-12 text-white sm:px-10 sm:py-16 lg:px-16">
            <div className="pointer-events-none absolute -right-12 -top-28 h-80 w-80 rounded-full border border-amber-200/20" aria-hidden="true" />
            <div className="pointer-events-none absolute -right-1 top-0 h-56 w-56 rounded-full border border-dashed border-amber-200/20" aria-hidden="true" />
            <div className="relative grid items-end gap-9 md:grid-cols-[1fr_auto]">
              <div className="max-w-3xl">
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-200">{t('aboutMissionEyebrow')}</p>
                <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight sm:text-4xl">{t('aboutMissionTitle')}</h2>
                <p className="mt-5 text-sm leading-7 text-emerald-50/90 sm:text-base">{t('aboutMissionText')}</p>
              </div>
              <Link to="/" className="inline-flex min-h-12 items-center justify-center gap-2 border border-white/30 px-5 py-3 text-sm font-semibold transition hover:border-amber-200 hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-amber-200">
                {t('aboutHomeLink')}<ArrowDownRight className="h-4 w-4 -rotate-45" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </section>
      </div>
    </PublicLayout>
  );
};
