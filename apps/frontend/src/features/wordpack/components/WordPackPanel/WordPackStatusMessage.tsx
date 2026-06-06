import React from 'react';

interface WordPackStatusMessageProps {
  message: { kind: 'status' | 'alert'; text: string } | null;
}

export const WordPackStatusMessage: React.FC<WordPackStatusMessageProps> = ({ message }) => {
  if (!message) return null;
  return <div className="wp-status-message" role={message.kind}>{message.text}</div>;
};
