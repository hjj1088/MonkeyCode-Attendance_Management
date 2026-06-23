// shared/matcher.js
// 跨文件数据匹配 - 考勤号为主键，姓名+部门为降级键

const Matcher = {
  async buildEmployeeMap() {
    const punchRecords = await Store.getAll('punch_records');
    const map = {};
    for (const rec of punchRecords) {
      if (rec.employeeNo && rec.name) {
        map[rec.employeeNo] = {
          name: rec.name,
          department: rec.department || ''
        };
      }
    }
    return map;
  },

  async syncEmployees() {
    const map = await this.buildEmployeeMap();
    const employees = Object.entries(map).map(([no, info]) => ({
      employeeNo: no,
      name: info.name,
      department: info.department
    }));
    await Store.clearTable('employees');
    await Store.bulkPut('employees', employees);
    return employees;
  },

  async resolveEmployeeNo(applicant, department) {
    const employees = await Store.getAll('employees');
    const match = employees.find(e =>
      e.name === applicant && e.department === department
    );
    return match ? match.employeeNo : null;
  },

  async matchOAToPunch(oaRecords, oaType) {
    const employeeMap = await this.buildEmployeeMap();
    const nameDeptToNo = {};
    for (const [no, info] of Object.entries(employeeMap)) {
      const key = `${info.name}|${info.department}`;
      nameDeptToNo[key] = no;
    }
    const matches = [];
    for (let i = 0; i < oaRecords.length; i++) {
      const rec = oaRecords[i];
      const key = `${rec.applicant}|${rec.department}`;
      const employeeNo = nameDeptToNo[key] || null;
      matches.push({ index: i, employeeNo, applicant: rec.applicant, department: rec.department });
    }
    return matches;
  }
};
