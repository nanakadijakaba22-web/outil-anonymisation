"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { DetectionReport, Dataset, AnonymizationResponse } from "@/lib/api";
import {
  getSensitivityColor,
  formatSensitivityType,
  formatTechnique,
} from "@/lib/utils";
import Stepper from "@/components/Stepper";
import ProgressBadge from "@/components/ProgressBadge";
import ProtectedRoute from "@/components/ProtectedRoute";
import Header from "@/components/Header";

interface TechniquePreview {
  column_name: string;
  sensitivity_type: string;
  technique: string;
  description: string;
}

// Map sensitivity types to automatic technique recommendations
function getAutomaticTechnique(sensitivityType: string, columnName: string, category?: string): TechniquePreview {
  const lowerName = columnName.toLowerCase();

  switch (sensitivityType) {
    case 'direct_identifier':
      if (lowerName.includes('nas') || lowerName.includes('ssn') || lowerName.includes('carte')) {
        return {
          column_name: columnName,
          sensitivity_type: sensitivityType,
          technique: 'suppression',
          description: 'Colonne completement supprimee (donnee ultra-sensible)'
        };
      }
      return {
        column_name: columnName,
        sensitivity_type: sensitivityType,
        technique: 'masking',
        description: 'Masquage avec 2 caracteres visibles (ex: je**@te**.com)'
      };

    case 'quasi_identifier':
      if (lowerName.includes('date') || lowerName.includes('naissance')) {
        return {
          column_name: columnName,
          sensitivity_type: sensitivityType,
          technique: 'generalization',
          description: 'Generalisation a l\'annee uniquement'
        };
      }
      return {
        column_name: columnName,
        sensitivity_type: sensitivityType,
        technique: 'generalization',
        description: 'Generalisation en 5 tranches ou prefixe'
      };

    case 'sensitive':
      if (category === 'financial' || lowerName.includes('revenu') || lowerName.includes('solde') || lowerName.includes('montant')) {
        return {
          column_name: columnName,
          sensitivity_type: sensitivityType,
          technique: 'differential_privacy',
          description: 'Confidentialite differentielle (epsilon=0.1, Laplace)'
        };
      }
      return {
        column_name: columnName,
        sensitivity_type: sensitivityType,
        technique: 'generalization',
        description: 'Generalisation en prefixe de 3 caracteres'
      };

    default:
      return {
        column_name: columnName,
        sensitivity_type: sensitivityType,
        technique: 'none',
        description: 'Aucune transformation (donnee non-sensible)'
      };
  }
}

export default function AnonymizationPage() {
  const router = useRouter();
  const params = useParams();
  const datasetId = params.id as string;

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [report, setReport] = useState<DetectionReport | null>(null);
  const [techniquesPreviews, setTechniquesPreviews] = useState<TechniquePreview[]>([]);
  const [processing, setProcessing] = useState(false);
  const [autoStarted, setAutoStarted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [anonymizationResult, setAnonymizationResult] = useState<AnonymizationResponse | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [datasetData, detectionReport] = await Promise.all([
          api.getDataset(datasetId),
          api.detectSensitiveData(datasetId),
        ]);

        setDataset(datasetData);
        setReport(detectionReport);

        // Build technique previews for display
        const previews: TechniquePreview[] = [];
        Object.entries(detectionReport.columns).forEach(
          ([columnName, classification]) => {
            if (classification.sensitivity_type !== 'non_sensitive') {
              previews.push(
                getAutomaticTechnique(
                  classification.sensitivity_type,
                  columnName,
                  classification.category
                )
              );
            }
          },
        );

        setTechniquesPreviews(previews);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Erreur lors du chargement",
        );
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [datasetId]);

  // Auto-start anonymization when page loads
  useEffect(() => {
    if (!loading && !autoStarted && report && !error) {
      setAutoStarted(true);
      handleAutoAnonymize();
    }
  }, [loading, autoStarted, report, error]);

  const handleAutoAnonymize = async () => {
    try {
      setProcessing(true);
      setError(null);

      const response = await api.autoAnonymizeDataset(datasetId);
      setAnonymizationResult(response);

      // Navigate to results page with the anonymized dataset ID
      router.push(`/results/${response.anonymized_dataset_id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erreur lors de l'anonymisation",
      );
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mb-4"></div>
          <h2 className="text-2xl font-semibold text-gray-800">
            Chargement...
          </h2>
        </div>
      </div>
    );
  }

  if (error && !processing) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="max-w-md bg-white rounded-lg shadow-xl p-8">
          <div className="text-red-600 mb-4">
            <svg
              className="w-12 h-12 mx-auto"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2 text-center">
            Erreur
          </h2>
          <p className="text-gray-600 text-center mb-4">{error}</p>
          <div className="flex gap-3">
            <button
              onClick={() => router.push("/")}
              className="flex-1 py-2 px-4 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
            >
              Retour a l'accueil
            </button>
            <button
              onClick={handleAutoAnonymize}
              className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Reessayer
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!report || !dataset) {
    return null;
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <Header />
        {/* Progress Badge */}
        <ProgressBadge
          currentStep="anonymization"
          completedSteps={["upload", "detection"]}
        />

        <div className="container mx-auto px-4 py-12">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              {processing ? "Anonymisation en cours..." : "Anonymisation automatique"}
            </h1>
            <p className="text-lg text-gray-600">{dataset.filename}</p>
            <p className="text-sm text-gray-500">
              {techniquesPreviews.length} colonnes a anonymiser
            </p>
          </div>

          {/* Stepper Navigation */}
          <Stepper
            currentStep="anonymization"
            datasetId={datasetId}
            completedSteps={["upload", "detection"]}
          />

          {/* Processing Animation */}
          {processing && (
            <div className="bg-white rounded-xl shadow-lg p-12 mb-8">
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-20 w-20 border-4 border-blue-200 border-t-blue-600 mb-6"></div>
                <h2 className="text-2xl font-semibold text-gray-800 mb-2">
                  Application des techniques d'anonymisation
                </h2>
                <p className="text-gray-600">
                  Les donnees sensibles sont en cours de protection selon les regles de la Loi 25...
                </p>
              </div>
            </div>
          )}

          {/* Technique Preview Cards */}
          {!processing && (
            <>
              {/* Info Banner */}
              <div className="bg-green-50 border-2 border-green-200 rounded-lg p-4 mb-8">
                <div className="flex items-start">
                  <svg
                    className="w-6 h-6 text-green-600 mr-3 flex-shrink-0 mt-0.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <div>
                    <h3 className="font-semibold text-green-900 mb-1">
                      Techniques selectionnees automatiquement
                    </h3>
                    <p className="text-sm text-green-800">
                      Les techniques d'anonymisation optimales ont ete choisies automatiquement
                      en fonction du type de donnees detecte. L'anonymisation demarrera automatiquement.
                    </p>
                  </div>
                </div>
              </div>

              {/* Techniques Table */}
              <div className="bg-white rounded-lg shadow-xl overflow-hidden mb-8">
                <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                  <h2 className="text-xl font-semibold text-gray-800">
                    Techniques a appliquer ({techniquesPreviews.length})
                  </h2>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                          Colonne
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                          Type
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                          Technique
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                          Description
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {techniquesPreviews.map((preview) => {
                        const colors = getSensitivityColor(preview.sensitivity_type);
                        return (
                          <tr key={preview.column_name} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="font-medium text-gray-900">{preview.column_name}</span>
                            </td>
                            <td className="px-6 py-4">
                              <span
                                className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${colors.bg} ${colors.text} border ${colors.border}`}
                              >
                                {formatSensitivityType(preview.sensitivity_type)}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <span className="inline-block px-3 py-1 rounded-lg text-sm font-medium bg-blue-100 text-blue-800">
                                {formatTechnique(preview.technique)}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <p className="text-sm text-gray-700">{preview.description}</p>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 justify-center">
                <button
                  onClick={() => router.push(`/detection/${datasetId}`)}
                  className="py-3 px-8 bg-gray-200 text-gray-800 rounded-lg font-semibold hover:bg-gray-300 transition-all"
                >
                  Retour a la detection
                </button>
                <button
                  onClick={handleAutoAnonymize}
                  disabled={processing}
                  className="py-3 px-8 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span className="flex items-center">
                    <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    Lancer l'anonymisation
                  </span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
