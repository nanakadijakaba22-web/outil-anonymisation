/**
 * Utility functions for the application
 */

import type { RiskScore } from './api';

// Format file size to human-readable format
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${Math.round(bytes / Math.pow(k, i) * 100) / 100} ${sizes[i]}`;
}

// Format date to locale string
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString('fr-CA', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Get color class based on sensitivity type
export function getSensitivityColor(
  sensitivityType: string | null
): { bg: string; text: string; border: string } {
  switch (sensitivityType) {
    case 'direct_identifier':
      return {
        bg: 'bg-red-100',
        text: 'text-red-800',
        border: 'border-red-300',
      };
    case 'quasi_identifier':
      return {
        bg: 'bg-orange-100',
        text: 'text-orange-800',
        border: 'border-orange-300',
      };
    case 'sensitive':
      return {
        bg: 'bg-blue-100',
        text: 'text-blue-800',
        border: 'border-blue-300',
      };
    case 'non_sensitive':
    default:
      return {
        bg: 'bg-green-100',
        text: 'text-green-800',
        border: 'border-green-300',
      };
  }
}

// Get color for risk level
export function getRiskLevelColor(level: string): { bg: string; text: string } {
  switch (level) {
    case 'faible':
      return { bg: 'bg-green-100', text: 'text-green-800' };
    case 'moyen':
      return { bg: 'bg-yellow-100', text: 'text-yellow-800' };
    case 'élevé':
      return { bg: 'bg-red-100', text: 'text-red-800' };
    default:
      return { bg: 'bg-gray-100', text: 'text-gray-800' };
  }
}

// Get risk gauge color
export function getRiskGaugeColor(score: number): string {
  if (score < 10) return '#10b981'; // green
  if (score < 25) return '#f59e0b'; // yellow
  return '#ef4444'; // red
}

// Format sensitivity type to French
export function formatSensitivityType(type: string | null): string {
  switch (type) {
    case 'direct_identifier':
      return 'Identifiant direct';
    case 'quasi_identifier':
      return 'Quasi-identifiant';
    case 'sensitive':
      return 'Sensible';
    case 'non_sensitive':
      return 'Non-sensible';
    default:
      return 'Non classé';
  }
}

// Format category to French according to Law 25
export function formatCategory(category: string | null): string {
  switch (category) {
    case 'Personnel':
    case 'personal':
      return 'Personnel';
    case 'Origine ethnique ou raciale':
    case 'ethnic_or_racial_origin':
    case 'ethnic':
    case 'racial':
      return 'Origine ethnique ou raciale';
    case 'Santé':
    case 'health':
      return 'Santé';
    case 'Financier':
    case 'financial':
      return 'Financier';
    case 'BIOMETRIQUE':
      return 'Biométrique';
    case 'GENETIQUE':
      return 'Génétique';
    case 'VIE SEXUELLE':
      return 'Vie sexuelle';
    case 'ORIENTATION SEXUELLE':
      return 'Orientation sexuelle';
    case 'RELIGION':
      return 'Religion';
    case 'PHILOSOPHIE':
      return 'Philosophie';
    case 'POLITIQUE':
      return 'Politique';
    case 'ETHNIQUE':
      return 'Ethnique';
    case 'RACIALE':
      return 'Raciale';
    case 'ASSURANCE':
      return 'Assurance';
    case 'Autre':
    case 'other':
    default:
      return 'Autre';
  }
}

// Format technique to French

export function formatTechnique(technique: string): string {
  switch (technique) {
    case 'masking':
      return 'Suppression';
    case 'generalization':
      return 'Généralisation';
    case 'suppression':
      return 'Suppression';
    case 'differential_privacy':
      return 'Confidentialité différentielle';
    case 'none':
    case 'keep_as_is':
      return 'Aucune';
    default:
      return technique;
  }
}

// Format technique with parameters for detailed display
export function formatTechniqueWithParams(
  technique: string,
  columnName: string,
  sensitivityType: string
): string {
  const lowerName = columnName.toLowerCase();

  switch (technique) {
    case 'suppression':
    case 'masking': // Often used interchangeably for total removal in this context
      return 'Suppression totale';

    case 'differential_privacy':
      return 'Confidentialité diff. (ε=1.0, sécurité modérée)';

    case 'generalization':
      // 1. Dates (BIRTHDATE, DEATHDATE, etc.)
      if (lowerName.includes('date') || lowerName.includes('naissance')) {
        return 'Année uniquement';
      }

      // 2. Race / Ethnie / Genre (Hierarchies/Categorical)
      if (
        lowerName.includes('race') ||
        lowerName.includes('ethnie') ||
        lowerName.includes('ethnicity')
      ) {
        return 'Regroupement de catégories';
      }

      if (lowerName.includes('gender') || lowerName.includes('sexe')) {
        return 'Normalisation catégorielle';
      }

      // 3. Géographie (ZIP, CITY, COUNTY, STATE, LAT, LON)
      if (
        lowerName.includes('ville') ||
        lowerName.includes('city') ||
        lowerName.includes('town') ||
        lowerName.includes('postal') ||
        lowerName.includes('zip') ||
        lowerName.includes('county') ||
        lowerName.includes('comté') ||
        lowerName.includes('state') ||
        lowerName.includes('état') ||
        lowerName.includes('region') ||
        lowerName.includes('pays') ||
        lowerName.includes('lat') ||
        lowerName.includes('lon')
      ) {
        return 'Généralisation géographique (escalade possible)';
      }

      // 4. Age and Numeric Tranches
      if (lowerName.includes('age')) {
        return 'Tranches d\'âge (10 ans)';
      }

      const numericKeywords = [
        'montant', 'nombre', 'revenu', 'salaire', 'solde', 'expenses', 'coverage'
      ];
      if (numericKeywords.some(key => lowerName.includes(key))) {
        return 'Généralisation par tranches';
      }

      // 5. Default: Prefix masking for other quasi-ids or sensitive text
      return 'Masquage (3 premiers car.)';

    case 'none':
      return 'Aucune transformation';

    default:
      return technique.charAt(0).toUpperCase() + technique.slice(1).replace('_', ' ');
  }
}


// Calculate percentage
export function calculatePercentage(value: number, total: number): number {
  if (total === 0) return 0;
  return Math.round((value / total) * 100);
}

// Truncate text
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

// Class name merger (simple version)
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

// Calculate re-identification risk score from sensitivity type
export function calculateColumnRiskScore(
  sensitivityType: string | null
): number {
  switch (sensitivityType) {
    case 'direct_identifier':
      return 92.5; // Risque élevé (85-100%)
    case 'quasi_identifier':
      return 67.5; // Risque moyen-élevé (60-75%)
    case 'sensitive':
      return 47.5; // Risque moyen (40-55%)
    case 'non_sensitive':
    default:
      return 17.5; // Risque faible (10-25%)
  }
}

// Get risk score color (similar to getSensitivityColor)
export function getRiskScoreColor(
  score: number
): { bg: string; text: string; border: string } {
  if (score >= 75) {
    // Risque élevé - Rouge
    return {
      bg: 'bg-red-100',
      text: 'text-red-800',
      border: 'border-red-300',
    };
  } else if (score >= 40) {
    // Risque moyen - Orange
    return {
      bg: 'bg-orange-100',
      text: 'text-orange-800',
      border: 'border-orange-300',
    };
  } else {
    // Risque faible - Vert
    return {
      bg: 'bg-green-100',
      text: 'text-green-800',
      border: 'border-green-300',
    };
  }
}
