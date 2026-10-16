import AppKit
import CoreText
import Foundation

// Font parsing mirrors Squirrel 1.1.2, including its family-face interpretation.
let input = CommandLine.arguments
guard input.count == 4 else { fatalError("usage: font-audit style.json corpus.json output.json") }
let style = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: input[1]))) as! [String: Any]
let corpus = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: input[2]))) as! [[String: Any]]
let familyFace = try NSRegularExpression(pattern: #"^\s*(.+)-([^-]+)\s*$"#)
func decodeFonts(_ chain: String, size: CGFloat) -> ([NSFont], [[String: Any]]) {
  var fonts = [NSFont]()
  var inventory = [[String: Any]]()
  var seen = Set<String>()
  for part in chain.split(separator: ",") {
    let raw = String(part)
    let requested = raw.trimmingCharacters(in: .whitespaces)
    var resolved: NSFont?
    if let match = familyFace.firstMatch(in: raw, range: NSRange(location: 0, length: raw.utf16.count)) {
      let family = (raw as NSString).substring(with: match.range(at: 1))
      let face = (raw as NSString).substring(with: match.range(at: 2))
      if seen.contains(family) { continue }
      resolved = NSFont(descriptor: NSFontDescriptor(fontAttributes: [.family: family, .face: face]), size: size)
      if resolved != nil { seen.insert(family) }
    }
    if resolved == nil {
      if seen.contains(requested) { continue }
      resolved = NSFont(descriptor: NSFontDescriptor(fontAttributes: [.name: requested]), size: size)
      if resolved != nil { seen.insert(requested) }
    }
    if let font = resolved {
      fonts.append(font)
      let ct = CTFontCreateWithName(font.fontName as CFString, size, nil)
      let url = CTFontCopyAttribute(ct, kCTFontURLAttribute) as? URL
      inventory.append(["requested": requested, "resolved": font.fontName, "family": font.familyName ?? "", "file": url?.lastPathComponent ?? ""])
    } else {
      inventory.append(["requested": requested, "resolved": NSNull()])
    }
  }
  return (fonts, inventory)
}
var results = [[String: Any]]()
for (field, sizeField) in [("font_face", "font_point"), ("label_font_face", "label_font_point"), ("comment_font_face", "comment_font_point"), ("preedit_font_face", "font_point")] {
  let size = (style[sizeField] as! NSNumber).doubleValue
  let (fonts, inventory) = decodeFonts(style[field] as! String, size: size)
  guard let first = fonts.first else { fatalError("No usable fonts") }
  let descriptor = first.fontDescriptor.addingAttributes([.cascadeList: fonts.dropFirst().map { $0.fontDescriptor }])
  let font = NSFont(descriptor: descriptor, size: size)!
  var cases = [[String: Any]]()
  var unifontCount = 0
  var missingCount = 0
  var fontCounts = [String: Int]()
  for sample in corpus {
    let text = sample["text"] as! String
    if text.isEmpty { continue }
    let line = CTLineCreateWithAttributedString(NSAttributedString(string: text, attributes: [.font: font]))
    var runs = [[String: Any]]()
    var unifont = false
    var missing = false
    for run in CTLineGetGlyphRuns(line) as! [CTRun] {
      let selected = (CTRunGetAttributes(run) as NSDictionary)[kCTFontAttributeName] as! CTFont
      let name = CTFontCopyPostScriptName(selected) as String
      let range = CTRunGetStringRange(run)
      let renderedText = (text as NSString).substring(with: NSRange(location: range.location, length: range.length))
      if name.lowercased().contains("unifont") { unifont = true }
      if name.lowercased().contains("lastresort") { missing = true }
      if text.unicodeScalars.count == 1 {
        var glyphs = [CGGlyph](repeating: 0, count: CTRunGetGlyphCount(run))
        CTRunGetGlyphs(run, CFRange(location: 0, length: 0), &glyphs)
        if glyphs.isEmpty || glyphs.contains(0) { missing = true }
      }
      fontCounts[name, default: 0] += 1
      runs.append(["font": name, "text": renderedText])
    }
    if unifont { unifontCount += 1 }
    if missing { missingCount += 1 }
    var entry = sample
    entry["runs"] = runs
    entry["unifont"] = unifont
    entry["missing"] = missing
    cases.append(entry)
  }
  results.append(["field": field, "size": size, "inventory": inventory, "unifont_count": unifontCount, "missing_count": missingCount, "font_counts": fontCounts, "cases": cases, "two_space_width": ("  " as NSString).size(withAttributes: [.font: font]).width])
  print("\(field): \(cases.count) samples, \(unifontCount) Unifont, \(missingCount) missing")
}
let output = try JSONSerialization.data(withJSONObject: results, options: [.prettyPrinted, .sortedKeys])
try output.write(to: URL(fileURLWithPath: input[3]))
