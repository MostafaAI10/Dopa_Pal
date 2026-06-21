import { GoogleGenerativeAI } from '@google/generative-ai';
import { config } from 'dotenv';
import path from 'path';
import { app } from 'electron';

// Load .env relative to the app root
config({ path: path.join(app.getAppPath(), '.env') });
const API_KEY = process.env.GEMINI_API_KEY;

let genAI = null;
if (API_KEY) {
  genAI = new GoogleGenerativeAI(API_KEY);
} else {
  console.warn("[AI] GEMINI_API_KEY is not set in .env. AI extraction will fail.");
}

const MODEL_NAME = 'gemini-1.5-flash';

const PROMPT = `You are an AI assistant helping a user manage their tasks.
Extract the following information from the user's input:
1. \`title\`: A short, actionable title for the task.
2. \`deadline\`: The deadline for the task in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ). If no deadline is mentioned, assume 7 days from now.
3. \`estimated_hours\`: A reasonable estimate for how many hours this task will take (float). If not mentioned, default to 2.0.
4. \`interest_tag\`: A single word category for the task (e.g., 'coding', 'health', 'finance', 'errand'). If not mentioned, return null.

The current date and time is: {current_time}

Respond ONLY with a valid JSON object matching this schema:
{
  "title": "string",
  "deadline": "string",
  "estimated_hours": 2.0,
  "interest_tag": "string | null"
}`;

function getCurrentTimeStr() {
  return new Date().toISOString();
}

function parseAIResponse(text) {
  let cleanText = text.trim();
  if (cleanText.startsWith('```json')) cleanText = cleanText.slice(7);
  else if (cleanText.startsWith('```')) cleanText = cleanText.slice(3);
  if (cleanText.endsWith('```')) cleanText = cleanText.slice(0, -3);

  try {
    const data = JSON.parse(cleanText);
    if (!data.deadline) {
      const d = new Date();
      d.setDate(d.getDate() + 7);
      data.deadline = d.toISOString();
    }
    return data;
  } catch (e) {
    console.error("Failed to parse Gemini JSON:", e, cleanText);
    const fallbackDate = new Date();
    fallbackDate.setDate(fallbackDate.getDate() + 7);
    return {
      title: "AI Task (Parsing Failed)",
      deadline: fallbackDate.toISOString(),
      estimated_hours: 2.0,
      interest_tag: null
    };
  }
}

export async function extractTaskFromText(text) {
  if (!genAI) throw new Error("GEMINI_API_KEY is not set in .env");
  
  const model = genAI.getGenerativeModel({ model: MODEL_NAME });
  const prompt = PROMPT.replace('{current_time}', getCurrentTimeStr()) + `\n\nUser Input: ${text}`;
  
  const result = await model.generateContent(prompt);
  return parseAIResponse(result.response.text());
}

export async function extractTaskFromAudio(audioBuffer) {
  if (!genAI) throw new Error("GEMINI_API_KEY is not set in .env");
  
  const model = genAI.getGenerativeModel({ model: MODEL_NAME });
  const prompt = PROMPT.replace('{current_time}', getCurrentTimeStr()) + "\n\nExtract the task details from the provided audio.";
  
  // Convert buffer to generative AI inlineData part
  const audioPart = {
    inlineData: {
      data: Buffer.from(audioBuffer).toString('base64'),
      mimeType: "audio/webm"
    }
  };

  const result = await model.generateContent([prompt, audioPart]);
  return parseAIResponse(result.response.text());
}
