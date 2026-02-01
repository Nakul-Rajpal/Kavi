const fs = require("fs");
const path = require("path");
const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  "https://iofndonrjbuubyjlgilt.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlvZm5kb25yamJ1dWJ5amxnaWx0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk4NjQ4OTYsImV4cCI6MjA4NTQ0MDg5Nn0._q9oE9ge2C1EDK5LTky4ySPvZHyQTqT243VddtbBEik"
);

async function uploadAndUpdate() {
  // Find any PNG file in the current directory
  const files = fs.readdirSync(__dirname);
  const pngFile = files.find(f => f.toLowerCase().endsWith('.png') && f.includes('Screenshot'));
  
  if (!pngFile) {
    console.error("No screenshot PNG found in directory!");
    console.log("Available files:", files.filter(f => f.endsWith('.png')));
    return;
  }

  const imagePath = path.join(__dirname, pngFile);
  console.log("Found image:", imagePath);
  
  return uploadFile(imagePath);
}

async function uploadFile(imagePath) {
  const imageBuffer = fs.readFileSync(imagePath);
  console.log("Image size:", imageBuffer.length, "bytes");

  const filename = "pothole_" + Date.now() + ".png";

  const { data: uploadData, error: uploadError } = await supabase.storage
    .from("frames")
    .upload(filename, imageBuffer, { contentType: "image/png" });

  if (uploadError) {
    console.error("Upload error:", uploadError);
    return;
  }
  console.log("Uploaded:", uploadData);

  const { data: urlData } = supabase.storage
    .from("frames")
    .getPublicUrl(filename);
  console.log("Public URL:", urlData.publicUrl);

  const { data: updateData, error: updateError } = await supabase
    .from("pings")
    .update({ image_url: urlData.publicUrl })
    .eq("id", "ae461047-d8a1-4f7b-85ec-29d57b6996d9")
    .select();

  if (updateError) {
    console.error("Update error:", updateError);
    return;
  }
  console.log("Updated ticket:", updateData);
}

uploadAndUpdate();

