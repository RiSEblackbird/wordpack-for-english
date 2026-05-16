import React from 'react';

interface WordPackStatusMessageProps {
  message: { kind: 'status' | 'alert'; text: string } | null;
}

export const WordPackStatusMessage: React.FC<WordPackStatusMessageProps> = ({ message }) => {
  if (!message) return null;
  return <div role={message.kind}>{message.text}</div>;
};
