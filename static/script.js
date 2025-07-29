document.addEventListener('DOMContentLoaded', () => {
    // --- Utility Function to handle messages ---
    const showMessage = (elementId, message, isSuccess) => {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = message;
            element.style.color = isSuccess ? 'green' : 'red';
        }
    };

    // --- Login Page Logic ---
    if (document.getElementById('loginForm')) {
        const loginForm = document.getElementById('loginForm');
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            try {
                const response = await fetch('/user/login', {
                    method: 'POST',
                    body: formData,
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage('message', data.message, true);
                    localStorage.setItem('loggedInUser', username);
                    window.location.href = '/dashboard';
                } else {
                    showMessage('message', data.error || 'Login failed.', false);
                }
            } catch (error) {
                console.error('Error during login:', error);
                showMessage('message', 'An error occurred. Please try again.', false);
            }
        });
    }

    // --- Registration Page Logic ---
    if (document.getElementById('registerForm')) {
        const registerForm = document.getElementById('registerForm');
        registerForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const username = document.getElementById('regUsername').value;
            const password = document.getElementById('regPassword').value;
            const salary = document.getElementById('regSalary').value; // Optional, can be empty

            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);
            if (salary) {
                formData.append('salary', salary); // Only append if provided
            }


            try {
                const response = await fetch('/user/add', {
                    method: 'POST',
                    body: formData,
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage('registerMessage', data.message + ' Redirecting to login...', true);
                    // Optionally redirect after a short delay
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                } else {
                    showMessage('registerMessage', data.error || 'Registration failed.', false);
                }
            } catch (error) {
                console.error('Error during registration:', error);
                showMessage('registerMessage', 'An error occurred during registration. Please try again.', false);
            }
        });
    }


    // --- Dashboard Page Logic ---
    if (document.getElementById('dashboardUsername')) {
        const loggedInUser = localStorage.getItem('loggedInUser');
        if (!loggedInUser) {
            window.location.href = '/login'; // Redirect if not logged in
            return;
        }

        document.getElementById('dashboardUsername').textContent = loggedInUser;

        const logoutButton = document.getElementById('logoutButton');
        logoutButton.addEventListener('click', () => {
            localStorage.removeItem('loggedInUser');
            window.location.href = '/login';
        });

        // Function to fetch and display financial summary
        const fetchFinancialSummary = async () => {
            try {
                const response = await fetch(`/summary/${loggedInUser}`);
                const data = await response.json();
                if (response.ok) {
                    document.getElementById('monthlySalary').textContent = data.monthly_salary !== undefined ? parseFloat(data.monthly_salary).toFixed(2) : 'N/A';
                    document.getElementById('totalMonthlyExpenses').textContent = data.total_monthly_expenses !== undefined ? parseFloat(data.total_monthly_expenses).toFixed(2) : 'N/A';
                    document.getElementById('totalMonthlyInvestments').textContent = data.total_monthly_investments !== undefined ? parseFloat(data.total_monthly_investments).toFixed(2) : 'N/A';
                    document.getElementById('remainingMonthlyBalance').textContent = data.remaining_monthly_balance !== undefined ? parseFloat(data.remaining_monthly_balance).toFixed(2) : 'N/A';
                    document.getElementById('totalExpensesOverall').textContent = data.total_expenses !== undefined ? parseFloat(data.total_expenses).toFixed(2) : 'N/A';
                    document.getElementById('totalInvestmentsOverall').textContent = data.total_investments !== undefined ? parseFloat(data.total_investments).toFixed(2) : 'N/A';

                } else {
                    console.error('Failed to fetch summary:', data.message);
                    document.getElementById('monthlySalary').textContent = 'Error';
                    document.getElementById('totalMonthlyExpenses').textContent = 'Error';
                    document.getElementById('totalMonthlyInvestments').textContent = 'Error';
                    document.getElementById('remainingMonthlyBalance').textContent = 'Error';
                    document.getElementById('totalExpensesOverall').textContent = 'Error';
                    document.getElementById('totalInvestmentsOverall').textContent = 'Error';
                }
            } catch (error) {
                console.error('Error fetching financial summary:', error);
                document.getElementById('monthlySalary').textContent = 'Error';
                document.getElementById('totalMonthlyExpenses').textContent = 'Error';
                document.getElementById('totalMonthlyInvestments').textContent = 'Error';
                document.getElementById('remainingMonthlyBalance').textContent = 'Error';
                document.getElementById('totalExpensesOverall').textContent = 'Error';
                document.getElementById('totalInvestmentsOverall').textContent = 'Error';
            }
        };

        // Function to fetch and display expenses
        const fetchExpenses = async () => {
            try {
                const response = await fetch(`/expense/get/${loggedInUser}`);
                const data = await response.json();
                const expensesList = document.getElementById('expensesList');
                expensesList.innerHTML = ''; // Clear previous list

                if (response.ok && data.length > 0) {
                    data.forEach(expense => {
                        const li = document.createElement('li');
                        li.textContent = `Date: ${expense.date}, Category: ${expense.category}, Amount: ${parseFloat(expense.amount).toFixed(2)}`;
                        expensesList.appendChild(li);
                    });
                } else {
                    expensesList.innerHTML = `<li>${data.message || 'No expenses recorded yet.'}</li>`;
                }
            } catch (error) {
                console.error('Error fetching expenses:', error);
                document.getElementById('expensesList').innerHTML = `<li>Error loading expenses.</li>`;
            }
        };

        // Function to fetch and display investments
        const fetchInvestments = async () => {
            try {
                const response = await fetch(`/investment/get/${loggedInUser}`);
                const data = await response.json();
                const investmentsList = document.getElementById('investmentsList');
                investmentsList.innerHTML = ''; // Clear previous list

                if (response.ok && data.length > 0) {
                    data.forEach(investment => {
                        const li = document.createElement('li');
                        li.textContent = `Symbol: ${investment.stock_symbol}, Shares: ${parseFloat(investment.shares).toFixed(2)}, Price: ${parseFloat(investment.purchase_price).toFixed(2)}, Date: ${investment.purchase_date}`;
                        investmentsList.appendChild(li);
                    });
                } else {
                    investmentsList.innerHTML = `<li>${data.message || 'No investments recorded yet.'}</li>`;
                }
            } catch (error) {
                console.error('Error fetching investments:', error);
                document.getElementById('investmentsList').innerHTML = `<li>Error loading investments.</li>`;
            }
        };

        // Function to fetch and display monthly investment breakdown
        const fetchMonthlyInvestmentBreakdown = async () => {
            try {
                const response = await fetch(`/investment/breakdown/${loggedInUser}`);
                const data = await response.json();
                const breakdownList = document.getElementById('investmentBreakdownList');
                breakdownList.innerHTML = ''; // Clear previous list

                if (response.ok && data.length > 0) {
                    data.forEach(plan => {
                        const li = document.createElement('li');
                        li.textContent = `${plan['Plan Name'] || 'N/A'}: ${plan['Investment Plan'] || 'N/A'} - Monthly: $${parseFloat(plan['Monthly Investment']).toFixed(2)} (${(parseFloat(plan['Percent of Salary']) * 100).toFixed(2)}%) - ${plan['Months Completed']}/${plan['Total Months']} months`;
                        breakdownList.appendChild(li);
                    });
                } else {
                    breakdownList.innerHTML = `<li>${data.error || 'No investment plans or salary not set for breakdown.'}</li>`;
                }
            } catch (error) {
                console.error('Error fetching investment breakdown:', error);
                document.getElementById('investmentBreakdownList').innerHTML = `<li>Error loading investment breakdown.</li>`;
            }
        };


        // Handle Expense Form Submission
        const expenseForm = document.getElementById('expenseForm');
        expenseForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const amount = document.getElementById('expenseAmount').value;
            const category = document.getElementById('expenseCategory').value;
            const date = document.getElementById('expenseDate').value;

            const formData = new FormData();
            formData.append('username', loggedInUser);
            formData.append('amount', amount);
            formData.append('category', category);
            formData.append('date', date);

            try {
                const response = await fetch('/expense/record', {
                    method: 'POST',
                    body: formData,
                });
                const data = await response.json();
                if (response.ok) {
                    showMessage('expenseMessage', data.message, true);
                    expenseForm.reset(); // Clear form
                    fetchExpenses(); // Refresh expenses list
                    fetchFinancialSummary(); // Refresh summary
                } else {
                    showMessage('expenseMessage', data.error || 'Failed to record expense.', false);
                }
            } catch (error) {
                console.error('Error recording expense:', error);
                showMessage('expenseMessage', 'An error occurred. Please try again.', false);
            }
        });

        // Handle Investment Form Submission
        const investmentForm = document.getElementById('investmentForm');
        investmentForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const stockSymbol = document.getElementById('stockSymbol').value;
            const shares = document.getElementById('shares').value;
            const purchasePrice = document.getElementById('purchasePrice').value;
            const purchaseDate = document.getElementById('purchaseDate').value;

            const formData = new FormData();
            formData.append('username', loggedInUser);
            formData.append('stock_symbol', stockSymbol);
            formData.append('shares', shares);
            formData.append('purchase_price', purchasePrice);
            formData.append('purchase_date', purchaseDate);

            try {
                const response = await fetch('/investment/record', {
                    method: 'POST',
                    body: formData,
                });
                const data = await response.json();
                if (response.ok) {
                    showMessage('investmentMessage', data.message, true);
                    investmentForm.reset(); // Clear form
                    fetchInvestments(); // Refresh investments list
                    fetchFinancialSummary(); // Refresh summary
                    fetchMonthlyInvestmentBreakdown(); // Refresh breakdown
                } else {
                    showMessage('investmentMessage', data.error || 'Failed to record investment.', false);
                }
            } catch (error) {
                console.error('Error recording investment:', error);
                showMessage('investmentMessage', 'An error occurred. Please try again.', false);
            }
        });


        // Initial data fetch when dashboard loads
        fetchFinancialSummary();
        fetchExpenses();
        fetchInvestments();
        fetchMonthlyInvestmentBreakdown();
    }
});