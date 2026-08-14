// shared/matcher.js
// 跨文件数据匹配 - 考勤号为主键，姓名+部门为降级键（纯函数，数据由调用方传入）

export const Matcher = {
  buildEmployeeMap(punchRecords) {
    const map = {};
    for (const rec of punchRecords || []) {
      if (rec.employeeNo && rec.name) {
        map[rec.employeeNo] = {
          name: rec.name,
          department: rec.department || '',
        };
      }
    }
    return map;
  },

  buildEmployees(punchRecords) {
    const map = this.buildEmployeeMap(punchRecords);
    return Object.entries(map).map(([no, info]) => ({
      employeeNo: no,
      name: info.name,
      department: info.department,
    }));
  },

  resolveEmployeeNo(employees, applicant, department) {
    const match = (employees || []).find(e =>
      e.name === applicant && e.department === department
    );
    return match ? match.employeeNo : null;
  },

  matchOAToPunch(oaRecords, employeeMap) {
    const nameDeptToNo = {};
    for (const [no, info] of Object.entries(employeeMap || {})) {
      const key = `${info.name}|${info.department}`;
      nameDeptToNo[key] = no;
    }
    const matches = [];
    for (let i = 0; i < (oaRecords || []).length; i++) {
      const rec = oaRecords[i];
      const key = `${rec.applicant}|${rec.department}`;
      const employeeNo = nameDeptToNo[key] || null;
      matches.push({ index: i, employeeNo, applicant: rec.applicant, department: rec.department });
    }
    return matches;
  },
};

export default Matcher;
