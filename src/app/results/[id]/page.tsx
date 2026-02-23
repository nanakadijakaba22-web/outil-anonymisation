'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { api } from '@/lib/api';
import type { RiskAssessment, Dataset } from '@/lib/api';
import { getRiskLevelColor, getRiskGaugeColor } from '@/lib/utils';
import Stepper from '@/components/Stepper';
import ProgressBadge from '@/components/ProgressBadge';
import InteractiveCharts from '@/components/InteractiveCharts';
import ProtectedRoute from '@/components/ProtectedRoute';
import Header from '@/components/Header';

export default function ResultsPage() {
  const router = useRouter();
  const params = useParams();
  const datasetId = params.id as string;

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [assessment, setAssessment] = useState<RiskAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadingReport, setDownloadingReport] = useState(false);

  useEffect(() => {
    const loadResults = async () => {
      try {
        setLoading(true);
        setError(null);

        const [datasetData, riskAssessment] = await Promise.all([
          api.getDataset(datasetId),
          api.assessRisk(datasetId),
        ]);

        setDataset(datasetData);
        setAssessment(riskAssessment);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur lors du chargement');
      } finally {
        setLoading(false);
      }
    };

    loadResults();
  }, [datasetId]);

  const handleDownload = async () => {
    try {
      setDownloading(true);
      const blob = await api.downloadDataset(datasetId);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = dataset?.filename || 'dataset_anonymized.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors du téléchargement');
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadReport = async () => {
    try {
      setDownloadingReport(true);
      const blob = await api.downloadComplianceReport(datasetId);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const filename = dataset?.filename.replace('.csv', '') || 'dataset';
      a.download = `rapport_loi25_${filename}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la génération du rapport');
    } finally {
      setDownloadingReport(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mb-4"></div>
          <h2 className="text-2xl font-semibold text-gray-800">
            Évaluation des risques en cours...
          </h2>
          <p className="text-gray-600 mt-2">Calcul de la conformité à la Loi 25</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="max-w-md bg-white rounded-lg shadow-xl p-8">
          <div className="text-red-600 mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2 text-center">Erreur</h2>
          <p className="text-gray-600 text-center mb-4">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retour à l'accueil
          </button>
        </div>
      </div>
    );
  }

  if (!assessment || !dataset) {
    return null;
  }

  const RiskGauge = ({ score, label }: { score: number; label: string }) => {
    const color = getRiskGaugeColor(score);
    const percentage = Math.min(score, 100);

    return (
      <div className="text-center">
        <div className="relative inline-block">
          <svg width="120" height="120" viewBox="0 0 120 120">
            <circle
              cx="60"
              cy="60"
              r="50"
              fill="none"
              stroke="#e5e7eb"
              strokeWidth="10"
            />
            <circle
              cx="60"
              cy="60"
              r="50"
              fill="none"
              stroke={color}
              strokeWidth="10"
              strokeDasharray={`${(percentage / 100) * 314} 314`}
              strokeLinecap="round"
              transform="rotate(-90 60 60)"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-2xl font-bold text-gray-800">
              {score > 0 && score < 0.1 ? '< 0.1%' : `${score.toFixed(1)}%`}
            </span>
          </div>
        </div>
        <p className="text-sm font-medium text-gray-700 mt-2">{label}</p>
      </div>
    );
  };

  const isCompliant = assessment.is_loi25_compliant;
  const overallColors = getRiskLevelColor(assessment.overall_level);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <Header />
        {/* Progress Badge */}
        <ProgressBadge
          currentStep="results"
          completedSteps={['upload', 'detection', 'anonymization']}
        />

      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Résultats de l'Évaluation
          </h1>
          <p className="text-lg text-gray-600">{dataset.filename}</p>
          {dataset.is_anonymized && (
            <span className="inline-block mt-2 px-4 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">
              Dataset anonymisé
            </span>
          )}
        </div>

        {/* Stepper Navigation */}
        <Stepper
          currentStep="results"
          datasetId={datasetId}
          completedSteps={['upload', 'detection', 'anonymization']}
        />

        {/* Compliance Status Banner */}
        <div
          className={`rounded-xl shadow-lg p-6 mb-8 ${
            isCompliant
              ? 'bg-green-50 border-2 border-green-300'
              : 'bg-red-50 border-2 border-red-300'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              {isCompliant ? (
                <svg className="w-12 h-12 text-green-600 mr-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="w-12 h-12 text-red-600 mr-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              <div>
                <h2 className={`text-2xl font-bold ${isCompliant ? 'text-green-900' : 'text-red-900'}`}>
                  {isCompliant ? 'CONFORME' : 'NON-CONFORME'} à la Loi 25
                </h2>
                <p className={`text-sm ${isCompliant ? 'text-green-800' : 'text-red-800'}`}>
                  Score global: {assessment.overall_score.toFixed(1)}% (Niveau: {assessment.overall_level})
                </p>
              </div>
            </div>
            <div className={`px-6 py-3 rounded-lg ${overallColors.bg} ${overallColors.text} font-semibold`}>
              {assessment.overall_level.toUpperCase()}
            </div>
          </div>
        </div>

        {/* Risk Criteria Gauges */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6 text-center">
            Critères d'Évaluation des Risques
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <RiskGauge score={assessment.individualization.score} label="Individualisation" />
              <div className="mt-4">
                <span
                  className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                    getRiskLevelColor(assessment.individualization.level).bg
                  } ${getRiskLevelColor(assessment.individualization.level).text}`}
                >
                  {assessment.individualization.level}
                </span>
                <p className="text-sm text-gray-600 mt-2">
                  {assessment.individualization.justification}
                </p>
                {assessment.individualization.affected_columns.length > 0 && (
                  <p className="text-xs text-gray-500 mt-2">
                    Colonnes: {assessment.individualization.affected_columns.slice(0, 3).join(', ')}
                    {assessment.individualization.affected_columns.length > 3 && '...'}
                  </p>
                )}
              </div>
            </div>

            <div>
              <RiskGauge score={assessment.correlation.score} label="Corrélation" />
              <div className="mt-4">
                <span
                  className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                    getRiskLevelColor(assessment.correlation.level).bg
                  } ${getRiskLevelColor(assessment.correlation.level).text}`}
                >
                  {assessment.correlation.level}
                </span>
                <p className="text-sm text-gray-600 mt-2">
                  {assessment.correlation.justification}
                </p>
                {assessment.correlation.affected_columns.length > 0 && (
                  <p className="text-xs text-gray-500 mt-2">
                    Colonnes: {assessment.correlation.affected_columns.slice(0, 3).join(', ')}
                    {assessment.correlation.affected_columns.length > 3 && '...'}
                  </p>
                )}
              </div>
            </div>

            <div>
              <RiskGauge score={assessment.inference.score} label="Inférence" />
              <div className="mt-4">
                <span
                  className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                    getRiskLevelColor(assessment.inference.level).bg
                  } ${getRiskLevelColor(assessment.inference.level).text}`}
                >
                  {assessment.inference.level}
                </span>
                <p className="text-sm text-gray-600 mt-2">
                  {assessment.inference.justification}
                </p>
                {assessment.inference.affected_columns.length > 0 && (
                  <p className="text-xs text-gray-500 mt-2">
                    Colonnes: {assessment.inference.affected_columns.slice(0, 3).join(', ')}
                    {assessment.inference.affected_columns.length > 3 && '...'}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Recommendations */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">
            Recommandations
          </h2>
          <ul className="space-y-3">
            {assessment.recommendations.map((recommendation, index) => (
              <li key={index} className="flex items-start">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-semibold mr-3 mt-0.5">
                  {index + 1}
                </span>
                <p className="text-gray-700">{recommendation}</p>
              </li>
            ))}
          </ul>
        </div>

        {/* Dataset Info */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">
            Informations sur le Dataset
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-600">Lignes</p>
              <p className="text-xl font-bold text-gray-800">{dataset.row_count}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Colonnes</p>
              <p className="text-xl font-bold text-gray-800">{dataset.column_count}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Score de risque</p>
              <p className="text-xl font-bold text-gray-800">
                {dataset.risk_score?.toFixed(1) || 'N/A'}%
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Statut</p>
              <p className={`text-xl font-bold ${isCompliant ? 'text-green-600' : 'text-red-600'}`}>
                {isCompliant ? 'Conforme' : 'Non-conforme'}
              </p>
            </div>
          </div>
        </div>

        {/* Interactive Visualizations */}
        <InteractiveCharts datasetId={datasetId} />

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={() => router.push('/')}
            className="py-3 px-8 bg-gray-200 text-gray-800 rounded-lg font-semibold hover:bg-gray-300 transition-all"
          >
            Nouveau fichier
          </button>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="py-3 px-8 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {downloading ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Téléchargement...
              </span>
            ) : (
              <span className="flex items-center justify-center">
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                Télécharger le CSV
              </span>
            )}
          </button>
          <button
            onClick={handleDownloadReport}
            disabled={downloadingReport}
            className="py-3 px-8 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {downloadingReport ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Génération du rapport...
              </span>
            ) : (
              <span className="flex items-center justify-center">
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Rapport PDF Loi 25
              </span>
            )}
          </button>
        </div>
      </div>
      </div>
    </ProtectedRoute>
  );
}
