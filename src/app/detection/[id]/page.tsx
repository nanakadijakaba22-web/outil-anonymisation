'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { api } from '@/lib/api';
import type { DetectionReport, Dataset } from '@/lib/api';
import {
  getSensitivityColor,
  formatSensitivityType,
  formatCategory,
} from '@/lib/utils';

export default function DetectionPage() {
  const router = useRouter();
  const params = useParams();
  const datasetId = params.id as string;

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [report, setReport] = useState<DetectionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const runDetection = async () => {
      try {
        setLoading(true);
        setError(null);

        // Load dataset metadata
        const datasetData = await api.getDataset(datasetId);
        setDataset(datasetData);

        // Run detection
        const detectionReport = await api.detectSensitiveData(datasetId);
        setReport(detectionReport);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur lors de la détection');
      } finally {
        setLoading(false);
      }
    };

    runDetection();
  }, [datasetId]);

  const handleContinue = () => {
    router.push(`/anonymization/${datasetId}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mb-4"></div>
          <h2 className="text-2xl font-semibold text-gray-800">
            Analyse des données sensibles en cours...
          </h2>
          <p className="text-gray-600 mt-2">
            Classification des colonnes selon la Loi 25
          </p>
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
          <h2 className="text-xl font-semibold text-gray-800 mb-2 text-center">
            Erreur de détection
          </h2>
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

  if (!report || !dataset) {
    return null;
  }

  const columnEntries = Object.entries(report.columns);
  const { summary } = report;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Résultats de la Détection
          </h1>
          <p className="text-lg text-gray-600">
            {dataset.filename}
          </p>
          <p className="text-sm text-gray-500">
            {dataset.row_count} lignes × {dataset.column_count} colonnes
          </p>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Identifiants directs</p>
                <p className="text-3xl font-bold text-red-600">{summary.direct_identifier}</p>
              </div>
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Quasi-identifiants</p>
                <p className="text-3xl font-bold text-orange-600">{summary.quasi_identifier}</p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Données sensibles</p>
                <p className="text-3xl font-bold text-blue-600">{summary.sensitive}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Non-sensibles</p>
                <p className="text-3xl font-bold text-green-600">{summary.non_sensitive}</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Overall Risk Score */}
        <div className="bg-white rounded-lg shadow-xl p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Score de Risque Global
          </h2>
          <div className="flex items-center">
            <div className="flex-1">
              <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all ${
                    report.overall_risk_score < 20
                      ? 'bg-green-500'
                      : report.overall_risk_score < 50
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(report.overall_risk_score, 100)}%` }}
                ></div>
              </div>
            </div>
            <div className="ml-4 text-3xl font-bold text-gray-800">
              {report.overall_risk_score.toFixed(1)}%
            </div>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            {report.overall_risk_score < 20
              ? 'Risque faible - Dataset potentiellement conforme'
              : report.overall_risk_score < 50
              ? 'Risque moyen - Anonymisation recommandée'
              : 'Risque élevé - Anonymisation requise pour la conformité Loi 25'}
          </p>
        </div>

        {/* Columns Detail */}
        <div className="bg-white rounded-lg shadow-xl p-8 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">
            Détail des Colonnes ({columnEntries.length})
          </h2>
          <div className="space-y-4">
            {columnEntries.map(([columnName, classification]) => {
              const colors = getSensitivityColor(classification.sensitivity_type);
              return (
                <div
                  key={columnName}
                  className={`border-2 ${colors.border} rounded-lg p-4 ${colors.bg}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-800">
                        {columnName}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span
                          className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${colors.bg} ${colors.text} border ${colors.border}`}
                        >
                          {formatSensitivityType(classification.sensitivity_type)}
                        </span>
                        <span className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-700 border border-gray-300">
                          {formatCategory(classification.category)}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-gray-800">
                        {Math.round(classification.confidence)}%
                      </div>
                      <div className="text-sm text-gray-600">Confiance</div>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 mt-3">
                    {classification.justification}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 justify-center">
          <button
            onClick={() => router.push('/')}
            className="py-3 px-8 bg-gray-200 text-gray-800 rounded-lg font-semibold hover:bg-gray-300 transition-all"
          >
            Nouveau fichier
          </button>
          <button
            onClick={handleContinue}
            className="py-3 px-8 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all shadow-md hover:shadow-lg"
          >
            Configurer l'anonymisation
          </button>
        </div>
      </div>
    </div>
  );
}
