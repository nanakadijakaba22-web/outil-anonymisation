'use client';

import { useRouter } from 'next/navigation';

export type StepId = 'upload' | 'detection' | 'anonymization' | 'results';

export interface Step {
  id: StepId;
  number: number;
  title: string;
  description: string;
  path: string;
}

interface StepperProps {
  currentStep: StepId;
  datasetId?: string;
  onNavigate?: (stepId: StepId) => void;
  completedSteps?: StepId[];
}

const steps: Step[] = [
  {
    id: 'upload',
    number: 1,
    title: 'Import',
    description: 'Téléversement CSV',
    path: '/',
  },
  {
    id: 'detection',
    number: 2,
    title: 'Analyse Initiale',
    description: 'Détection & Risque',
    path: '/detection/:id',
  },
  {
    id: 'anonymization',
    number: 3,
    title: 'Anonymisation',
    description: 'Configuration',
    path: '/anonymization/:id',
  },
  {
    id: 'results',
    number: 4,
    title: 'Post-Analyse',
    description: 'Résultats & Rapport',
    path: '/results/:id',
  },
];

export default function Stepper({
  currentStep,
  datasetId,
  onNavigate,
  completedSteps = [],
}: StepperProps) {
  const router = useRouter();

  const getCurrentStepIndex = () => {
    return steps.findIndex((step) => step.id === currentStep);
  };

  const isStepCompleted = (stepId: StepId): boolean => {
    return completedSteps.includes(stepId);
  };

  const isStepAccessible = (stepId: StepId): boolean => {
    // Upload is always accessible
    if (stepId === 'upload') return true;

    // Other steps require a datasetId
    if (!datasetId) return false;

    const targetIndex = steps.findIndex((s) => s.id === stepId);
    const currentIndex = getCurrentStepIndex();

    // Can access current step and completed steps
    if (stepId === currentStep) return true;
    if (isStepCompleted(stepId)) return true;

    // Can access next step if current is completed
    if (targetIndex === currentIndex + 1 && isStepCompleted(currentStep)) {
      return true;
    }

    return false;
  };

  const handleStepClick = (step: Step) => {
    if (!isStepAccessible(step.id)) return;

    if (onNavigate) {
      onNavigate(step.id);
    } else {
      // Default navigation behavior
      const path = step.path.replace(':id', datasetId || '');
      router.push(path);
    }
  };

  return (
    <div className="w-full bg-white shadow-md rounded-lg p-6 mb-8">
      {/* Desktop Stepper */}
      <div className="hidden md:block">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => {
            const isActive = step.id === currentStep;
            const isCompleted = isStepCompleted(step.id);
            const isAccessible = isStepAccessible(step.id);

            return (
              <div key={step.id} className="flex items-center flex-1">
                {/* Step Circle */}
                <button
                  onClick={() => handleStepClick(step)}
                  disabled={!isAccessible}
                  className={`
                    group relative flex flex-col items-center
                    ${isAccessible ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}
                  `}
                >
                  {/* Circle */}
                  <div
                    className={`
                      w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg
                      transition-all duration-200 border-2
                      ${isCompleted
                        ? 'bg-green-600 text-white border-green-600'
                        : isActive
                          ? 'bg-blue-600 text-white border-blue-600 ring-4 ring-blue-100'
                          : 'bg-gray-100 text-gray-400 border-gray-300'
                      }
                      ${isAccessible && !isActive ? 'group-hover:border-blue-400 group-hover:bg-blue-50' : ''}
                    `}
                  >
                    {isCompleted ? (
                      <svg
                        className="w-6 h-6"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={3}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    ) : (
                      step.number
                    )}
                  </div>

                  {/* Label */}
                  <div className="mt-2 text-center">
                    <div
                      className={`
                        text-sm font-semibold
                        ${isActive ? 'text-blue-600' : isCompleted ? 'text-green-600' : 'text-gray-500'}
                      `}
                    >
                      {step.title}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">{step.description}</div>
                  </div>

                  {/* Tooltip on hover */}
                  {!isAccessible && (
                    <div className="absolute top-full mt-2 hidden group-hover:block z-10">
                      <div className="bg-gray-800 text-white text-xs rounded py-1 px-2 whitespace-nowrap">
                        Complétez l'étape précédente
                      </div>
                    </div>
                  )}
                </button>

                {/* Connector Line */}
                {index < steps.length - 1 && (
                  <div className="flex-1 h-1 mx-4 mb-8">
                    <div
                      className={`
                        h-full rounded transition-all duration-300
                        ${isStepCompleted(steps[index + 1].id) || isCompleted
                          ? 'bg-green-600'
                          : isActive
                            ? 'bg-gradient-to-r from-blue-600 to-gray-300'
                            : 'bg-gray-300'
                        }
                      `}
                    ></div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Mobile Stepper */}
      <div className="md:hidden">
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm font-semibold text-gray-600">
            Étape {getCurrentStepIndex() + 1} sur {steps.length}
          </div>
          <div className="text-sm text-gray-500">
            {Math.round(((getCurrentStepIndex() + 1) / steps.length) * 100)}% complété
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-500"
            style={{
              width: `${((getCurrentStepIndex() + 1) / steps.length) * 100}%`,
            }}
          ></div>
        </div>

        {/* Current Step Info */}
        <div className="flex items-center">
          <div
            className={`
              w-10 h-10 rounded-full flex items-center justify-center font-bold text-white
              ${isStepCompleted(currentStep) ? 'bg-green-600' : 'bg-blue-600'}
            `}
          >
            {isStepCompleted(currentStep) ? (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              steps[getCurrentStepIndex()].number
            )}
          </div>
          <div className="ml-3">
            <div className="text-base font-semibold text-gray-800">
              {steps[getCurrentStepIndex()].title}
            </div>
            <div className="text-sm text-gray-500">
              {steps[getCurrentStepIndex()].description}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
