'use client';

import { StepId } from './Stepper';

interface ProgressBadgeProps {
  currentStep: StepId;
  completedSteps: StepId[];
}

const stepOrder: StepId[] = ['upload', 'detection', 'anonymization', 'results'];

export default function ProgressBadge({ currentStep, completedSteps }: ProgressBadgeProps) {
  const currentIndex = stepOrder.indexOf(currentStep);
  const totalSteps = stepOrder.length;

  // Calculate progress percentage
  // Each step is 25% (for 4 steps)
  const progressPercentage = Math.round(((currentIndex + 1) / totalSteps) * 100);

  // Determine status and color
  const isComplete = completedSteps.includes(currentStep);
  const statusColor = isComplete
    ? 'bg-green-100 text-green-800 border-green-300'
    : 'bg-blue-100 text-blue-800 border-blue-300';

  const statusIcon = isComplete ? (
    <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ) : (
    <svg className="w-4 h-4 mr-1 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );

  const stepNames: Record<StepId, string> = {
    upload: 'Import',
    detection: 'Analyse',
    anonymization: 'Anonymisation',
    results: 'Résultats',
  };

  return (
    <div className="fixed top-4 right-4 z-50 flex items-center gap-2">
      {/* Progress percentage badge */}
      <div className="bg-white shadow-lg rounded-full px-4 py-2 flex items-center border-2 border-gray-200">
        <div className="flex items-center">
          <svg className="w-5 h-5 text-blue-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="font-semibold text-gray-800 text-sm">
            {progressPercentage}%
          </span>
          <span className="text-xs text-gray-500 ml-2">
            ({currentIndex + 1}/{totalSteps})
          </span>
        </div>
      </div>

      {/* Current step badge */}
      <div
        className={`${statusColor} shadow-lg rounded-full px-4 py-2 flex items-center border-2 font-medium text-sm`}
      >
        {statusIcon}
        <span>{isComplete ? 'Complété' : stepNames[currentStep]}</span>
      </div>
    </div>
  );
}
