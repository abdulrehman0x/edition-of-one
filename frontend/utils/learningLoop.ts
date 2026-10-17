// frontend/utils/learningLoop.ts

export interface ReaderSignal {
  topic: string;
  weight: number; // +1 for liked/clicked, -1 for disliked
  timestamp: string;
}

export function logReaderSignal(topic: string, action: 'like' | 'dislike' | 'click' | 'save') {
  const weights: { [key: string]: number } = {
    like: 1.5,
    save: 2.0,
    click: 1.0,
    dislike: -2.0,
  };

  const signalWeight = weights[action] || 1.0;
  
  const existingSignals: ReaderSignal[] = JSON.parse(localStorage.getItem("edition_one_signals") || "[]");
  existingSignals.push({
    topic: topic.toLowerCase(),
    weight: signalWeight,
    timestamp: new Date().toISOString(),
  });

  localStorage.setItem("edition_one_signals", JSON.stringify(existingSignals));
}

// Compute aggregate topic multipliers to send to the backend
export function getLearnedProfileModifiers() {
  const signals: ReaderSignal[] = JSON.parse(localStorage.getItem("edition_one_signals") || "[]");
  const topicScores: { [key: string]: number } = {};

  signals.forEach(s => {
    topicScores[s.topic] = (topicScores[s.topic] || 1.0) + s.weight;
  });

  return topicScores;
}