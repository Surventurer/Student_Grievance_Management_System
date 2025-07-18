// Test file to diagnose school-department relationship
console.log("--- Starting School-Department Relationship Diagnosis ---");

// Function to fetch departments for a school
async function fetchDepartments(schoolId) {
    try {
        console.log(`Fetching departments for school ID: ${schoolId}`);
        const response = await fetch(`http://127.0.0.1:8000/auth/load-departments/?school_id=${schoolId}`);
        const data = await response.json();
        console.log(`Response status: ${response.status}`);
        console.log(`Response data:`, data);
        return data;
    } catch (error) {
        console.error(`Error fetching departments: ${error}`);
        return null;
    }
}

// Test with School of Arts and Sciences (ID: 12)
fetchDepartments(12).then(data => {
    console.log("Departments for School of Arts and Sciences:", data ? data.departments.length : "No data");
    if (data && data.departments.length > 0) {
        console.log("Sample departments:", data.departments.slice(0, 3));
    }
});

// Test with School of Engineering (ID: 10)
fetchDepartments(10).then(data => {
    console.log("Departments for School of Engineering:", data ? data.departments.length : "No data");
    if (data && data.departments.length > 0) {
        console.log("Sample departments:", data.departments.slice(0, 3));
    }
});

console.log("--- End of School-Department Relationship Diagnosis ---");
