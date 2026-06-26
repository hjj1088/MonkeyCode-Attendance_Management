const XLSX = require('./lib/xlsx.full.min.js');
const fs = require('fs');

console.log('XLSX version:', XLSX.version);

const ws = {};
ws['!ref'] = 'A1:C2';

ws['A1'] = { t: 's', v: 'Red Font', s: { font: { color: { rgb: 'FFFF0000' } } } };
ws['B1'] = { t: 's', v: 'Blue Font', s: { font: { color: { rgb: 'FF0066CC' } } } };
ws['C1'] = { t: 's', v: 'Gray Fill', s: { fill: { fgColor: { rgb: 'FFD9D9D9' }, patternType: 'solid' } } };
ws['A2'] = { t: 's', v: 'Normal' };
ws['B2'] = { t: 's', v: '迟10min', s: { font: { color: { rgb: 'FFFF0000' } } } };
ws['C2'] = { t: 's', v: '请假', s: { font: { color: { rgb: 'FF0066CC' } } } };

// Log cell styles
Object.keys(ws).filter(k => k !== '!ref').forEach(ref => {
    const cell = ws[ref];
    console.log(ref, JSON.stringify(cell));
});

const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, ws, 'Test');

// Try different write approaches
console.log('\n--- Write tests ---');

// Approach 1: type 'array'
const out1 = XLSX.write(wb, { bookType: 'xlsx', type: 'array', cellStyles: true });
console.log('type:array result type:', typeof out1, 'constructor:', out1?.constructor?.name, 'length:', out1?.length);
if (out1) {
    fs.writeFileSync('test1.xlsx', Buffer.from(out1));
    console.log('test1.xlsx saved');
}

// Approach 2: type 'buffer' (Node.js specific)
const out2 = XLSX.write(wb, { bookType: 'xlsx', type: 'buffer', cellStyles: true });
console.log('type:buffer result type:', typeof out2, 'constructor:', out2?.constructor?.name, 'length:', out2?.length);
if (out2) {
    fs.writeFileSync('test2.xlsx', out2);
    console.log('test2.xlsx saved');
}

// Approach 3: type 'binary' + Buffer
const out3 = XLSX.write(wb, { bookType: 'xlsx', type: 'binary', cellStyles: true });
console.log('type:binary result type:', typeof out3, 'length:', out3?.length);
if (out3) {
    fs.writeFileSync('test3.xlsx', Buffer.from(out3, 'binary'));
    console.log('test3.xlsx saved');
}

// Approach 4: type 'base64'
const out4 = XLSX.write(wb, { bookType: 'xlsx', type: 'base64', cellStyles: true });
console.log('type:base64 result type:', typeof out4, 'length:', out4?.length);

// Check if styles.xml exists in the output
console.log('\n--- Checking for styles.xml ---');
for (const f of ['test1.xlsx', 'test2.xlsx', 'test3.xlsx']) {
    try {
        const data = fs.readFileSync(f);
        const idx = data.indexOf('styles.xml');
        console.log(f + ': styles.xml found at offset', idx, 'size:', data.length, 'bytes');
    } catch(e) {
        console.log(f + ': error - ' + e.message);
    }
}

// Check the sheet XML content
console.log('\n--- Sheet XML check ---');
['test1.xlsx', 'test2.xlsx'].forEach(f => {
    try {
        const data = fs.readFileSync(f);
        const sheetIdx = data.indexOf('sheet1.xml');
        console.log(f + ': sheet1.xml at offset', sheetIdx);
        // Find style-related attributes in the ZIP
        // Look for fill, font, colorRef, indexedColors in the raw bytes
        const fillIdx = data.indexOf('fill>');
        const fontIdx = data.indexOf('font>');
        console.log('  fill> at', fillIdx, 'font> at', fontIdx);
    } catch(e) {}
});
