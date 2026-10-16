import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Calendar,
  CloudSun,
  Globe,
  Layers,
  MessageSquare,
  Moon,
  ScanLine,
  ShieldCheck,
  Sun,
  WifiOff,
} from 'lucide-react';
import { PublicLayout } from '../components/layout/PublicLayout';
import { getDefaultHomeForRole } from '../components/layout/ProtectedRoute';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import heroFarmImg from '../assets/images/hero_ethiopian_maize_farm_1791572380074.jpg';
import leafInspectionImg from '../assets/images/maize_leaf_inspection_1791572392418.jpg';
import extensionFieldImg from '../assets/images/extension_advisory_field_1791572402850.jpg';

export const LandingPage: React.FC = () => {
  const { t, language, setLanguage, theme, toggleTheme } = useApp();
  const { isAuthenticated, effectiveRole } = useAuth();
  const navigate = useNavigate();

  const [heroImgFailed, setHeroImgFailed] = useState(false);
  const [leafImgFailed, setLeafImgFailed] = useState(false);
  const [extImgFailed, setExtImgFailed] = useState(false);

  const handleDiagnoseClick = () => {
    if (isAuthenticated && effectiveRole) {
      navigate(effectiveRole === 'farmer' ? '/farmer/diagnose' : getDefaultHomeForRole(effectiveRole));
    } else {
      navigate('/login');
    }
  };

  return (
    <PublicLayout>
      {/* Workspace Utility Strip below Top Bar */}
      <div className="border-b border-stone-200/70 dark:border-stone-800/70 bg-white/70 dark:bg-[#101814]/70 px-6 py-2.5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 text-xs text-stone-600 dark:text-stone-400">
          <div className="flex items-center gap-2">
            <span className="font-medium text-emerald-900 dark:text-emerald-300">{t('heroKicker')}</span>
            <span aria-hidden="true">·</span>
            <span>MobileNetV2 & Grad-CAM Architecture</span>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 p-0.5 rounded-lg bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700">
              <button
                type="button"
                onClick={() => setLanguage('en')}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  language === 'en'
                    ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                    : 'text-stone-600 dark:text-stone-400 hover:text-stone-900'
                }`}
              >
                English
              </button>
              <button
                type="button"
                onClick={() => setLanguage('am')}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  language === 'am'
                    ? 'bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-xs'
                    : 'text-stone-600 dark:text-stone-400 hover:text-stone-900'
                }`}
              >
                አማርኛ
              </button>
            </div>

            <button
              type="button"
              onClick={toggleTheme}
              className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-700 dark:text-stone-300 hover:bg-stone-50 dark:hover:bg-stone-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              {theme === 'light' ? <Moon className="w-3.5 h-3.5" /> : <Sun className="w-3.5 h-3.5" />}
              <span>{theme === 'light' ? t('darkTheme') : t('lightTheme')}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-6 py-14 lg:py-20">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-stretch">
          <div className="lg:col-span-6 flex flex-col justify-center">
            <p className="text-xs font-medium text-emerald-800 dark:text-emerald-400 mb-3">
              {t('brandSubtitle')}
            </p>
            <h1
              className="font-display font-bold tracking-tight text-stone-900 dark:text-stone-100 leading-[1.12] max-w-2xl"
              style={{ fontSize: 'clamp(2.25rem, 4vw, 3.5rem)', textWrap: 'balance' }}
            >
              {t('heroTitle')}
            </h1>
            <p className="mt-5 text-base text-stone-600 dark:text-stone-300 leading-relaxed max-w-[62ch]">
              {t('heroDescription')}
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button
                type="button"
                onClick={handleDiagnoseClick}
                className="inline-flex items-center gap-2 px-6 py-3 text-sm font-semibold text-white bg-emerald-900 hover:bg-emerald-800 dark:bg-emerald-700 dark:hover:bg-emerald-600 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                <ScanLine className="w-4 h-4" />
                <span>{t('diagnoseLeaf')}</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <a
                href="#workflow"
                className="inline-flex items-center justify-center px-5 py-3 text-sm font-medium text-stone-800 dark:text-stone-200 bg-white dark:bg-[#121A16] border border-stone-300 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                {t('learnHowItWorks')}
              </a>
            </div>

            <div className="mt-10 pt-6 border-t border-stone-200 dark:border-stone-800 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-stone-600 dark:text-stone-400">
              <span>MobileNetV2 Classification</span>
              <span aria-hidden="true">·</span>
              <span>Grad-CAM Visual Heatmaps</span>
              <span aria-hidden="true">·</span>
              <span>English & Amharic Advisory</span>
              <span aria-hidden="true">·</span>
              <span>Woreda Extension Integration</span>
            </div>
          </div>

          <div className="lg:col-span-6 flex">
            <div className="relative w-full rounded-2xl overflow-hidden border border-stone-200 dark:border-stone-800 bg-emerald-950 min-h-[320px] lg:min-h-[440px]">
              {!heroImgFailed ? (
                <img
                  src={heroFarmImg}
                  alt="Terraced green maize fields in the Ethiopian highlands at golden hour"
                  referrerPolicy="no-referrer"
                  onError={() => setHeroImgFailed(true)}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center text-emerald-100 bg-gradient-to-br from-emerald-950 to-stone-900">
                  <ScanLine className="w-10 h-10 mb-3 text-amber-400" />
                  <p className="text-sm font-semibold">Ethiopian Highland Maize Cultivation</p>
                </div>
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent flex flex-col justify-end p-6 sm:p-8">
                <p className="text-xs font-mono text-amber-300">
                  POST /api/diagnosis/complete · MobileNetV2 + Grad-CAM
                </p>
                <p className="mt-1 text-sm sm:text-base font-medium text-white max-w-lg">
                  Built for smallholder farmers, woreda extension specialists, and regional agricultural administrators.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works — 4 Editorial Steps */}
      <section id="workflow" className="border-t border-stone-200 dark:border-stone-800 bg-white dark:bg-[#101814] py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="max-w-2xl">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900 dark:text-stone-100 font-display">
              {t('workflowHeading')}
            </h2>
            <p className="mt-2 text-sm sm:text-base text-stone-600 dark:text-stone-400">
              {t('workflowSubheading')}
            </p>
          </div>

          <div className="mt-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { title: t('step1Title'), desc: t('step1Desc') },
              { title: t('step2Title'), desc: t('step2Desc') },
              { title: t('step3Title'), desc: t('step3Desc') },
              { title: t('step4Title'), desc: t('step4Desc') },
            ].map((step) => (
              <div
                key={step.title}
                className="rounded-xl border border-stone-200 dark:border-stone-800 bg-[#FAF8F5] dark:bg-[#141E19] p-6 flex flex-col justify-between"
              >
                <div>
                  <h3 className="text-base font-semibold text-stone-900 dark:text-stone-100 font-display">
                    {step.title}
                  </h3>
                  <p className="mt-3 text-sm text-stone-600 dark:text-stone-400 leading-relaxed">
                    {step.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Capabilities — Asymmetric Bento Grid */}
      <section id="capabilities" className="max-w-7xl mx-auto px-6 py-16 lg:py-20">
        <div className="max-w-2xl mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900 dark:text-stone-100 font-display">
            Integrated Agronomic & Extension Architecture
          </h2>
          <p className="mt-2 text-sm sm:text-base text-stone-600 dark:text-stone-400">
            Connected directly to the Flask backend services for diagnosis, weather, crop calendars, community discussion, and outbreak management.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Card 1: Col-span-2 */}
          <div className="lg:col-span-2 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden grid grid-cols-1 md:grid-cols-12">
            <div className="md:col-span-7 p-6 sm:p-8 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-xs text-emerald-800 dark:text-emerald-400 font-medium">
                  <Layers className="w-4 h-4" />
                  <span>Explainable Deep Learning</span>
                </div>
                <h3 className="mt-2 text-xl font-bold text-stone-900 dark:text-stone-100 font-display">
                  Leaf Disease Classification with Grad-CAM Heatmaps
                </h3>
                <p className="mt-3 text-sm text-stone-600 dark:text-stone-400 leading-relaxed">
                  Uploads are processed by the TensorFlow MobileNetV2 classifier via{' '}
                  <code className="font-mono text-xs">/api/diagnosis/complete</code>. When explainability is enabled, the system serves a Grad-CAM activation overlay showing which foliar lesions influenced the prediction.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-stone-200/70 dark:border-stone-800 text-xs text-stone-500 dark:text-stone-400">
                Supports JPG, JPEG, PNG, WEBP up to 5 MB · Automatic history persistence
              </div>
            </div>
            <div className="md:col-span-5 bg-stone-900 min-h-[220px]">
              {!leafImgFailed ? (
                <img
                  src={leafInspectionImg}
                  alt="Farmer inspecting a green maize leaf in daylight"
                  referrerPolicy="no-referrer"
                  onError={() => setLeafImgFailed(true)}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center p-6 text-stone-400 text-xs">
                  Maize Leaf Inspection
                </div>
              )}
            </div>
          </div>

          {/* Card 2: Weather & Crop Calendar */}
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400 font-medium">
                <CloudSun className="w-4 h-4" />
                <span>Agro-Meteorology & Phenology</span>
              </div>
              <h3 className="mt-2 text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                Local Weather & Regional Crop Calendar
              </h3>
              <p className="mt-3 text-sm text-stone-600 dark:text-stone-400 leading-relaxed">
                Uses farmer profile coordinates and woreda configuration to retrieve live meteorological readings and seasonal maize crop-calendar stages.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-stone-200/70 dark:border-stone-800 flex items-center gap-2 text-xs text-stone-500 dark:text-stone-400">
              <Calendar className="w-3.5 h-3.5" />
              <span>Location-aware agronomic scheduling</span>
            </div>
          </div>

          {/* Card 3: Offline Queue */}
          <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-xs text-emerald-800 dark:text-emerald-400 font-medium">
                <WifiOff className="w-4 h-4" />
                <span>Resilient Field Workflow</span>
              </div>
              <h3 className="mt-2 text-lg font-bold text-stone-900 dark:text-stone-100 font-display">
                Offline Queue & Batch Synchronization
              </h3>
              <p className="mt-3 text-sm text-stone-600 dark:text-stone-400 leading-relaxed">
                When field connectivity drops, farmers can queue leaf images with unique operation IDs and synchronize them individually or in batches of up to 10 via{' '}
                <code className="font-mono text-xs">/api/sync/batch</code> once back online.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-stone-200/70 dark:border-stone-800 text-xs text-stone-500 dark:text-stone-400">
              Preserves operation ID to image association
            </div>
          </div>

          {/* Card 4: Extension & Community Col-span-2 */}
          <div className="lg:col-span-2 rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] overflow-hidden grid grid-cols-1 md:grid-cols-12">
            <div className="md:col-span-5 bg-stone-900 min-h-[220px]">
              {!extImgFailed ? (
                <img
                  src={extensionFieldImg}
                  alt="Agricultural extension specialist advising an Ethiopian maize farmer in the field"
                  referrerPolicy="no-referrer"
                  onError={() => setExtImgFailed(true)}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center p-6 text-stone-400 text-xs">
                  Extension Advisory Collaboration
                </div>
              )}
            </div>
            <div className="md:col-span-7 p-6 sm:p-8 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-xs text-emerald-800 dark:text-emerald-400 font-medium">
                  <MessageSquare className="w-4 h-4" />
                  <span>Multi-Role Collaboration</span>
                </div>
                <h3 className="mt-2 text-xl font-bold text-stone-900 dark:text-stone-100 font-display">
                  Extension Agent Workspaces, Community Board & Outbreak Alerts
                </h3>
                <p className="mt-3 text-sm text-stone-600 dark:text-stone-400 leading-relaxed">
                  Farmers post field questions to the discussion board; extension agents monitor woreda-assigned cases and geographic disease distributions; administrators manage regional statistics, outbreak evaluations, SMS alerts, and PDF/CSV reports.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-stone-200/70 dark:border-stone-800 text-xs text-stone-500 dark:text-stone-400">
                Role-separated workspaces for Farmers, Extension Agents, and Administrators
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Bilingual Support Section */}
      <section id="languages" className="border-t border-stone-200 dark:border-stone-800 bg-white dark:bg-[#101814] py-16 px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-7">
            <div className="flex items-center gap-2 text-xs font-medium text-emerald-800 dark:text-emerald-400">
              <Globe className="w-4 h-4" />
              <span>Bilingual Interface & Advisory</span>
            </div>
            <h2 className="mt-2 text-2xl sm:text-3xl font-bold tracking-tight text-stone-900 dark:text-stone-100 font-display">
              Native English and Amharic (አማርኛ) Support
            </h2>
            <p className="mt-3 text-sm sm:text-base text-stone-600 dark:text-stone-400 leading-relaxed max-w-2xl">
              Farmers and extension officers can switch seamlessly between English and Amharic. Diagnosis requests pass the selected language code (<code className="font-mono text-xs">en</code> or <code className="font-mono text-xs">am</code>) directly to the backend advisory service while preserving scientific disease nomenclature.
            </p>
          </div>
          <div className="lg:col-span-5 rounded-xl border border-stone-200 dark:border-stone-800 bg-[#FAF8F5] dark:bg-[#141E19] p-6 space-y-4">
            <div>
              <div className="text-xs text-stone-500 dark:text-stone-400">English Interface</div>
              <p className="mt-1 text-sm font-medium text-stone-900 dark:text-stone-100">
                Upload a maize leaf image to receive treatment and prevention recommendations.
              </p>
            </div>
            <div className="pt-4 border-t border-stone-200 dark:border-stone-800">
              <div className="text-xs text-stone-500 dark:text-stone-400">የአማርኛ ገጽታ (Amharic)</div>
              <p className="mt-1 text-sm font-medium text-stone-900 dark:text-stone-100">
                የበቆሎ ቅጠል ምስል በመጫን የህክምና እና የመከላከያ ምክሮችን በአማርኛ ያግኙ።
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Decision Support Notice */}
      <section id="decision-support" className="max-w-7xl mx-auto px-6 py-16">
        <div className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-[#121A16] p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-start gap-4 max-w-3xl">
            <ShieldCheck className="w-6 h-6 text-emerald-800 dark:text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <h2 className="text-base font-bold text-stone-900 dark:text-stone-100 font-display">
                {t('decisionSupportTitle')}
              </h2>
              <p className="mt-1.5 text-sm text-stone-600 dark:text-stone-400 leading-relaxed">
                {t('decisionSupportBody')}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link
              to="/register"
              className="px-5 py-2.5 text-xs font-semibold text-white bg-emerald-900 hover:bg-emerald-800 dark:bg-emerald-700 dark:hover:bg-emerald-600 rounded-lg transition-colors whitespace-nowrap"
            >
              {t('register')}
            </Link>
            <Link
              to="/login"
              className="px-5 py-2.5 text-xs font-medium text-stone-700 dark:text-stone-300 border border-stone-300 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 rounded-lg transition-colors whitespace-nowrap"
            >
              {t('signIn')}
            </Link>
          </div>
        </div>
      </section>
    </PublicLayout>
  );
};
