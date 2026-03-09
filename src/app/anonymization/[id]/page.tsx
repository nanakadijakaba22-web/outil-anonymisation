"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { DetectionReport, Dataset, ColumnClassification } from "@/lib/api";
import {
  getSensitivityColor,
  formatSensitivityType,
  formatTechniqueWithParams,
  formatCategory,
} from "@/lib/utils";
import Stepper from "@/components/Stepper";
import ProgressBadge from "@/components/ProgressBadge";
import ProtectedRoute from "@/components/ProtectedRoute";
import Header from "@/components/Header";

interface ColumnToTransform {
  column_name: string;
  sensitivity_type: string;
  category: string;
  risk_score: number;
  confidence: number;
  technique: string;
}

// Map sensitivity types to automatic technique recommendations
function getAutomaticTechnique(sensitivityType: string, columnName: string, category?: string): string {
  const lowerName = columnName.toLowerCase();

  switch (sensitivityType) {
    case 'direct_identifier':
      return 'suppression';

    case 'quasi_identifier':
      // Backend automatically suppresses ADDRESS
      if (lowerName.includes('address') || lowerName.includes('adresse')) {
        return 'suppression';
      }
      return 'generalization';

    case 'sensitive':
      // Priority for Differential Privacy on numeric healthcare/financial data
      if (
        category === 'financial' ||
        category === 'health' ||
        lowerName.includes('revenu') ||
        lowerName.includes('solde') ||
        lowerName.includes('montant') ||
        lowerName.includes('expense') ||
        lowerName.includes('coverage')
      ) {
        return 'differential_privacy';
      }
      return 'generalization';

    default:
      return 'none';
  }
}

// Get risk score color based on value
function getRiskColor(score: number): { bg: string; text: string } {
  if (score >= 70) {
    return { bg: 'bg-red-100', text: 'text-red-700' };
  } else if (score >= 40) {
    return { bg: 'bg-orange-100', text: 'text-orange-700' };
  } else {
    return { bg: 'bg-green-100', text: 'text-green-700' };
  }
}

// Calculate risk score based on sensitivity type if not provided
function calculateRiskScore(sensitivityType: string): number {
  switch (sensitivityType) {
    case 'direct_identifier':
      return 92;
    case 'quasi_identifier':
      return 68;
    case 'sensitive':
      return 48;
    default:
      return 18;
  }
}

export default function AnonymizationPage() {
  const router = useRouter();
  const params = useParams();
  const datasetId = params.id as string;

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [report, setReport] = useState<DetectionReport | null>(null);
  const [columnsToTransform, setColumnsToTransform] = useState<ColumnToTransform[]>([]);
  const [processing, setProcessing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Récupérer le dataset avec ses colonnes déjà classifiées
        const datasetData = await api.getDataset(datasetId);
        setDataset(datasetData);

        // Construire le rapport à partir des colonnes du dataset (déjà détectées)
        if (datasetData.columns && datasetData.columns.length > 0) {
          const columnsRecord: Record<string, ColumnClassification> = {};
          let directCount = 0;
          let quasiCount = 0;
          let sensitiveCount = 0;
          let nonSensitiveCount = 0;

          datasetData.columns.forEach((col) => {
            const sensType = col.sensitivity_type || 'non_sensitive';
            columnsRecord[col.name] = {
              column_name: col.name,
              sensitivity_type: sensType as any,
              category: (col.category || 'other') as any,
              confidence: col.confidence || 0,
              justification: '',
            };

            // Compter les types
            if (sensType === 'direct_identifier') directCount++;
            else if (sensType === 'quasi_identifier') quasiCount++;
            else if (sensType === 'sensitive') sensitiveCount++;
            else nonSensitiveCount++;
          });

          const detectionReport: DetectionReport = {
            dataset_id: datasetId,
            columns: columnsRecord,
            overall_risk_score: datasetData.risk_score || 0,
            summary: {
              direct_identifier: directCount,
              quasi_identifier: quasiCount,
              sensitive: sensitiveCount,
              non_sensitive: nonSensitiveCount,
            },
          };

          setReport(detectionReport);

          // Build list of columns to transform (exclude non_sensitive)
          const columns: ColumnToTransform[] = [];
          Object.entries(detectionReport.columns).forEach(
            ([columnName, classification]) => {
              // Only include columns that need transformation
              if (classification.sensitivity_type !== 'non_sensitive') {
                columns.push({
                  column_name: columnName,
                  sensitivity_type: classification.sensitivity_type,
                  category: classification.category || 'other',
                  risk_score: calculateRiskScore(classification.sensitivity_type),
                  confidence: classification.confidence || 0,
                  technique: getAutomaticTechnique(
                    classification.sensitivity_type,
                    columnName,
                    classification.category
                  ),
                });
              }
            },
          );

          setColumnsToTransform(columns);
        } else {
          setError("Aucune donnée de détection trouvée. Veuillez d'abord effectuer la détection.");
        }
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

  const handleAnonymize = async () => {
    try {
      setProcessing(true);
      setError(null);

      const response = await api.autoAnonymizeDataset(datasetId);
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
              onClick={() => window.location.reload()}
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
              {processing ? "Anonymisation en cours..." : "Configuration de l'anonymisation"}
            </h1>
            <p className="text-lg text-gray-600">{dataset.filename}</p>
            <p className="text-sm text-gray-500">
              {columnsToTransform.length} colonnes a anonymiser sur {Object.keys(report.columns).length} colonnes au total
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
              <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 mb-8">
                <div className="flex items-start">
                  <svg
                    className="w-6 h-6 text-blue-600 mr-3 flex-shrink-0 mt-0.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <div>
                    <h3 className="font-semibold text-blue-900 mb-1">
                      Verifiez les techniques recommandees
                    </h3>
                    <p className="text-sm text-blue-800">
                      Les techniques d'anonymisation optimales ont ete selectionnees automatiquement
                      en fonction du type de sensibilite de chaque colonne. Consultez le tableau ci-dessous
                      puis cliquez sur <strong>"Anonymiser"</strong> pour appliquer ces transformations.
                    </p>
                  </div>
                </div>
              </div>

              {/* Techniques Table */}
              <div className="bg-white rounded-lg shadow-xl overflow-hidden mb-8">
                <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                  <h2 className="text-xl font-semibold text-gray-800">
                    Colonnes a transformer ({columnsToTransform.length})
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
                          Categorie
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                          Risque
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                          Confiance
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                          Methode
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {columnsToTransform.map((column) => {
                        const sensitivityColors = getSensitivityColor(column.sensitivity_type);
                        const riskColors = getRiskColor(column.risk_score);
                        return (
                          <tr key={column.column_name} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="font-medium text-gray-900">
                                {column.column_name}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <span
                                className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${sensitivityColors.bg} ${sensitivityColors.text} border ${sensitivityColors.border}`}
                              >
                                {formatSensitivityType(column.sensitivity_type)}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <span className="text-sm text-gray-700">
                                {formatCategory(column.category)}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <span
                                className={`inline-block px-3 py-1 rounded-lg text-sm font-semibold ${riskColors.bg} ${riskColors.text}`}
                              >
                                {Math.round(column.risk_score)}%
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <span className="text-sm text-gray-700">
                                {Math.round(column.confidence)}%
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <span className="inline-block px-3 py-1 rounded-lg text-sm font-medium bg-blue-100 text-blue-800">
                                {formatTechniqueWithParams(column.technique, column.column_name, column.sensitivity_type)}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col items-center gap-4">
                <button
                  onClick={handleAnonymize}
                  disabled={processing || columnsToTransform.length === 0}
                  className="py-4 px-12 bg-blue-600 text-white rounded-xl font-bold text-lg hover:bg-blue-700 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105"
                >
                  <span className="flex items-center">
                    <svg className="w-6 h-6 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    Anonymiser
                  </span>
                </button>
                <button
                  onClick={() => router.push(`/detection/${datasetId}`)}
                  className="py-2 px-6 text-gray-600 hover:text-gray-800 font-medium transition-all"
                >
                  Retour a la detection
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
