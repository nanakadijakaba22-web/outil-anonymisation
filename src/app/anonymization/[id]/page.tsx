'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { api } from '@/lib/api';
import type { DetectionReport, Dataset, AnonymizationConfig } from '@/lib/api';
import {
  getSensitivityColor,
  formatSensitivityType,
  formatTechnique,
} from '@/lib/utils';
import Stepper from '@/components/Stepper';
import ProgressBadge from '@/components/ProgressBadge';
import ProtectedRoute from '@/components/ProtectedRoute';
import Header from '@/components/Header';

type TechniqueType = 'masking' | 'generalization' | 'suppression'  |'differential_privacy';

interface ColumnConfig {
  column_name: string;
  technique: TechniqueType;
  params: Record<string, any>;
  sensitivity_type: string;
}

export default function AnonymizationPage() {
  const router = useRouter();
  const params = useParams();
  const datasetId = params.id as string;

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [report, setReport] = useState<DetectionReport | null>(null);
  const [configs, setConfigs] = useState<Record<string, ColumnConfig>>({});
  const [processing, setProcessing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

        // Initialize configs with recommended techniques
        const initialConfigs: Record<string, ColumnConfig> = {};
        Object.entries(detectionReport.columns).forEach(([columnName, classification]) => {
          // Only configure columns that need anonymization
          if (
            classification.sensitivity_type === 'direct_identifier' ||
            classification.sensitivity_type === 'quasi_identifier' ||
            classification.sensitivity_type === 'sensitive'
          ) {
            // Recommend technique based on sensitivity and category
            let technique: TechniqueType = 'masking';
            let params: Record<string, any> = {};

            if (classification.sensitivity_type === 'direct_identifier') {
              if (classification.category === 'personal') {
                // NAS, email, phone -> suppression or masking
                if (columnName.toLowerCase().includes('nas')) {
                  technique = 'suppression';
                } else {
                  technique = 'masking';
                  params = { visible_chars: 2 };
                }
              }  else {
                   technique = 'differential_privacy';
                    params = { epsilon: 1.0, mechanism: 'laplace' };
                  }

              } else if (classification.sensitivity_type === 'quasi_identifier') {
                    technique = 'generalization';

                     const col = columnName.toLowerCase();

               // Code postal => préfixe
                if (col.includes('code_postal') || col.includes('postal') || col.includes('zip')) {
                   params = { mode: 'prefix', prefix_length: 3 };
                  }
              // Date => année
                else if (col.includes('date') || col.includes('ouverture')) {
                   params = { mode: 'year' };
              }
                // Sinon => bins (numérique)
                else {
                   params = { mode: 'bins', bins: 5 };
              }
              }

            initialConfigs[columnName] = {
              column_name: columnName,
              technique,
              params,
              sensitivity_type: classification.sensitivity_type,
            };
          }
        });

        setConfigs(initialConfigs);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur lors du chargement');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [datasetId]);

  const updateTechnique = (columnName: string, technique: TechniqueType) => {
    setConfigs((prev) => {
      const updated = { ...prev };
      updated[columnName] = {
        ...updated[columnName],
        technique,
        params: getDefaultParams(technique, columnName),
      };
      return updated;
    });
  };

  const updateParam = (columnName: string, paramName: string, value: any) => {
    setConfigs((prev) => {
      const updated = { ...prev };
      updated[columnName] = {
        ...updated[columnName],
        params: {
          ...updated[columnName].params,
          [paramName]: value,
        },
      };
      return updated;
    });
  };

  const getDefaultParams = (technique: TechniqueType, columnName?: string): Record<string, any> => {
    switch (technique) {
      case 'masking':
        return { visible_chars: 2 };
      case 'generalization':
        // Détection intelligente du mode selon le nom de la colonne
        if (columnName) {
          const col = columnName.toLowerCase();

          // Code postal => préfixe
          if (col.includes('code_postal') || col.includes('postal') || col.includes('zip') ||
              col.includes('ville') || col.includes('city') || col.includes('nom') ||
              col.includes('prenom') || col.includes('name')) {
            return { mode: 'prefix', prefix_length: 3 };
          }
          // Date => année
          else if (col.includes('date') || col.includes('ouverture')) {
            return { mode: 'year' };
          }
        }
        // Par défaut => bins (numérique)
        return { mode: 'bins', bins: 5 };
      case 'suppression':
        return {};
      case 'differential_privacy':
        return { epsilon: 1.0, delta:1e-5, mechanism: 'gaussian' };
      default:
        return {};
    }
  };

  const handleAnonymize = async () => {
    try {
      setProcessing(true);
      setError(null);

      const configArray: AnonymizationConfig[] = Object.values(configs).map((config) => {
        // Nettoyer les params: enlever 'mode' car le backend ne l'utilise pas
        const cleanParams = { ...config.params };
        delete cleanParams.mode;

        return {
          column_name: config.column_name,
          technique: config.technique,
          params: cleanParams,
        };
      });

      const response = await api.anonymizeDataset(datasetId, configArray);

      // Navigate to results page with the anonymized dataset ID
      router.push(`/results/${response.anonymized_dataset_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de l\'anonymisation');
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mb-4"></div>
          <h2 className="text-2xl font-semibold text-gray-800">Chargement...</h2>
        </div>
      </div>
    );
  }

  if (error && !processing) {
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

  if (!report || !dataset) {
    return null;
  }

  const configEntries = Object.entries(configs);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <Header />
        {/* Progress Badge */}
        <ProgressBadge currentStep="anonymization" completedSteps={['upload', 'detection']} />

      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Configuration de l'Anonymisation
          </h1>
          <p className="text-lg text-gray-600">{dataset.filename}</p>
          <p className="text-sm text-gray-500">
            {configEntries.length} colonnes à anonymiser
          </p>
        </div>

        {/* Stepper Navigation */}
        <Stepper
          currentStep="anonymization"
          datasetId={datasetId}
          completedSteps={['upload', 'detection']}
        />

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
                Techniques d'anonymisation recommandées
              </h3>
              <p className="text-sm text-blue-800">
                Les techniques ont été pré-sélectionnées en fonction du type de données.
                Vous pouvez les ajuster selon vos besoins.
              </p>
            </div>
          </div>
        </div>

        {/* Configuration Cards */}
        <div className="space-y-6 mb-8">
          {configEntries.map(([columnName, config]) => {
            const colors = getSensitivityColor(config.sensitivity_type);
            return (
              <div key={columnName} className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-800">{columnName}</h3>
                    <span
                      className={`inline-block mt-1 px-3 py-1 rounded-full text-sm font-medium ${colors.bg} ${colors.text} border ${colors.border}`}
                    >
                      {formatSensitivityType(config.sensitivity_type)}
                    </span>
                  </div>
                </div>

                {/* Technique Selector */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Technique d'anonymisation
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {(['masking', 'generalization', 'suppression', 'differential_privacy'] as TechniqueType[]).map(
                      (tech) => (
                        <button
                          key={tech}
                          onClick={() => updateTechnique(columnName, tech)}
                          className={`p-3 rounded-lg border-2 text-sm font-medium transition-all ${
                            config.technique === tech
                              ? 'border-blue-500 bg-blue-50 text-blue-700'
                              : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                          }`}
                        >
                          {formatTechnique(tech)}
                        </button>
                      )
                    )}
                  </div>
                </div>

                {/* Parameters */}
                {config.technique === 'masking' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Caractères visibles
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="10"
                      value={config.params.visible_chars || 2}
                      onChange={(e) =>
                        updateParam(columnName, 'visible_chars', parseInt(e.target.value))
                      }
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <p className="text-sm text-gray-500 mt-1">
                      Exemple: jean@test.com → je**@te**.com
                    </p>
                  </div>
                )}

              {config.technique === 'generalization' && (
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Mode de généralisation
                    </label>
                    <select
                      value={config.params.mode || 'bins'}
                      onChange={(e) => {
                        const mode = e.target.value;
                        const newParams: Record<string, any> = { mode };

                        // Définir les paramètres par défaut selon le mode
                        if (mode === 'bins') {
                          newParams.bins = 5;
                        } else if (mode === 'prefix') {
                          newParams.prefix_length = 3;
                        }
                        // mode 'year' ne nécessite pas de params supplémentaires

                        setConfigs(prev => ({
                          ...prev,
                          [columnName]: {
                            ...prev[columnName],
                            params: newParams
                          }
                        }));
                      }}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="bins">Tranches (numérique)</option>
                      <option value="prefix">Préfixe (texte/code postal)</option>
                      <option value="year">Année (dates)</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Mode automatiquement sélectionné selon le type de données
                    </p>
                  </div>

                  {/* Paramètres pour mode bins */}
                  {config.params.mode === 'bins' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Nombre de tranches
                      </label>
                      <input
                        type="number"
                        min="2"
                        max="10"
                        value={config.params.bins || 5}
                        onChange={(e) => updateParam(columnName, 'bins', parseInt(e.target.value))}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <p className="text-sm text-gray-500 mt-1">
                        Exemple: 75000 → "(50000, 100000]"
                      </p>
                    </div>
                  )}

                  {/* Paramètres pour mode prefix */}
                  {config.params.mode === 'prefix' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Longueur du préfixe
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="6"
                        value={config.params.prefix_length || 3}
                        onChange={(e) => updateParam(columnName, 'prefix_length', parseInt(e.target.value))}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <p className="text-sm text-gray-500 mt-1">
                        Exemple: "Montreal" → "Mon ***"
                      </p>
                    </div>
                  )}

                  {/* Info pour mode year */}
                  {config.params.mode === 'year' && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <p className="text-sm text-blue-800">
                        Les dates seront généralisées à l'année uniquement.
                        <br />
                        Exemple: "2021-08-22" → 2021
                      </p>
                    </div>
                  )}
                </div>
              )}


                {config.technique === 'differential_privacy' && (
  <div className="space-y-3">
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Epsilon (ε)
      </label>
      <input
        type="number"
        step="0.1"
        min="0.1"
        value={config.params.epsilon ?? 1.0}
        onChange={(e) => updateParam(columnName, 'epsilon', parseFloat(e.target.value))}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />
      <p className="text-sm text-gray-500 mt-1">
        Plus ε est petit, plus c’est privé (mais plus de bruit).
      </p>
    </div>

    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Mécanisme
      </label>
      <select
        value={config.params.mechanism ?? 'laplace'}
        onChange={(e) => updateParam(columnName, 'mechanism', e.target.value)}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg"
      >
        <option value="laplace">Laplace</option>
        <option value="gaussian">Gaussian</option>
      </select>
    </div>

    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <p className="text-sm text-yellow-800">
        <strong>Note :</strong> la confidentialité différentielle s’applique surtout aux colonnes numériques.
        Pour texte (nom, email), préfère suppression/masquage.
      </p>
    </div>
  </div>
)}


                {config.technique === 'suppression' && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-sm text-red-800">
                      <strong>Attention:</strong> Cette colonne sera complètement supprimée du
                      dataset anonymisé.
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4 justify-center">
          <button
            onClick={() => router.push(`/detection/${datasetId}`)}
            disabled={processing}
            className="py-3 px-8 bg-gray-200 text-gray-800 rounded-lg font-semibold hover:bg-gray-300 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Retour à la détection
          </button>
          <button
            onClick={handleAnonymize}
            disabled={processing || configEntries.length === 0}
            className="py-3 px-8 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {processing ? (
              <span className="flex items-center">
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
                Anonymisation en cours...
              </span>
            ) : (
              'Lancer l\'anonymisation'
            )}
          </button>
        </div>
      </div>
      </div>
    </ProtectedRoute>
  );
}
